"""Patient 360 Streamlit-in-Snowflake page.

Chart rows come from the active Snowpark session. Cited answers are assembled
from those rows. AI_COMPLETE is optional and is discarded when it leaves the
retrieved citation.
"""

from __future__ import annotations

import html
import sys
from collections.abc import Callable
from pathlib import Path

import streamlit as st

try:
    from snowflake.snowpark.context import get_active_session
except ImportError:
    get_active_session = None

_CANDIDATES = (
    Path(__file__).resolve().parents[1],
    Path(__file__).resolve().parent,
)
for _candidate in _CANDIDATES:
    if (_candidate / "app" / "__init__.py").is_file() and str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

try:
    from chrome import answer_card, ask_heading, inject, mark
    from app.assemble import assemble_answer, resolve_patient_id
    from app.banner import BANNER, POINT_RULES
    from app.constants import WORKED_PATIENT_ID
    from app.models import Answer
    from app.narrate import (
        DEFAULT_AI_COMPLETE_MODEL,
        NARRATION_SQL,
        accept_narration,
        build_narration_prompt,
    )
    from app.queries import (
        QuerySpec,
        allergy_query,
        allergy_section_query,
        antihistamine_query,
        care_plan_evidence_query,
        chart_queries,
        claim_evidence_query,
        condition_evidence_query,
        coverage_evidence_query,
        document_section_query,
        immunization_evidence_query,
        lab_evidence_query,
        medication_evidence_query,
        medication_section_query,
        member_summary_query,
        patient_list_query,
        patient_name_query,
        population_query,
        procedure_evidence_query,
        recent_encounter_query,
        risk_query,
    )
    from app.questions import (
        ALLERGY_QUESTION,
        CARE_PLAN_QUESTION,
        CLAIM_QUESTION,
        CONDITION_QUESTION,
        DISCHARGE_QUESTION,
        DOSE_QUESTION,
        FROZEN_QUESTIONS,
        LAB_QUESTION,
        MEDICATION_LIST_QUESTION,
        MEMBER_SUMMARY_QUESTION,
        OPENFDA_QUESTION,
        RISK_QUESTION,
        TREATMENT_QUESTION,
    )
    from app.retrieve import retrieval_steps
    from app.rows import normalize_row
    from app.text_parse import synthea_name
except ImportError:
    st.error(
        "The app package is not on the path. Stage app/ next to this file, "
        "or keep it in the parent of the streamlit directory."
    )
    st.stop()


class QueryFailure(Exception):
    """A warehouse statement failed. The page does not replace it with rows."""

    def __init__(self, name: str, detail: str) -> None:
        super().__init__(detail)
        self.name = name
        self.detail = detail


_SELECTED_ANTIHISTAMINE = (
    "Which antihistamine is on the medication list, and where is it written?"
)

_PATIENT_EVIDENCE: tuple[tuple[str, Callable[[str], QuerySpec]], ...] = (
    ("member_summary", member_summary_query),
    ("condition_evidence", condition_evidence_query),
    ("medication_evidence", medication_evidence_query),
    ("care_plan_evidence", care_plan_evidence_query),
    ("lab_evidence", lab_evidence_query),
    ("procedure_evidence", procedure_evidence_query),
    ("immunization_evidence", immunization_evidence_query),
    ("claim_evidence", claim_evidence_query),
    ("coverage_evidence", coverage_evidence_query),
)

_CHART_TITLES = {
    "encounter_counts": "Encounters by class",
    "encounters": "Latest encounters",
    "conditions": "Conditions",
    "medications": "Medications",
    "lab_count": "Laboratory count",
    "labs": "Latest laboratory results",
    "claim_count": "Claim count",
    "claim_line_count": "Claim line count",
    "claim_on_encounter": "One claim joined to its encounter",
    "coverage": "Coverage spans",
}


def main() -> None:
    st.set_page_config(page_title="Patient 360", layout="wide")
    inject()
    session = open_session()
    patients = load_patients(session)
    view, _ignored = navigation(patients, session)
    selected = member_bar(patients)
    patient_id = None if selected is None else str(selected["patient_id"])
    if view == "Chart":
        chart_page(session, selected)
    elif view == "Risk":
        cohort_page(session)
    else:
        ask_page(session, patient_id, selected)
    data_notice()


def open_session() -> object | None:
    if get_active_session is not None:
        try:
            return get_active_session()
        except Exception:
            pass
    try:
        return st.connection("snowflake").session()
    except Exception:
        return None


def load_patients(session: object | None) -> list[dict[str, str | None]]:
    if session is None:
        return []
    try:
        return fetch(session, patient_list_query())
    except QueryFailure as exc:
        show_query_error(exc)
        return []


def navigation(
    patients: list[dict[str, str | None]],
    session: object | None,
) -> tuple[str, dict[str, str | None] | None]:
    with st.sidebar:
        mark(84)
        st.markdown('<p class="p360-brand">PATIENT 360</p>', unsafe_allow_html=True)
        st.caption("Synthetic chart. Not for care.")
        view = st.radio("View", ("Ask", "Chart", "Risk"), label_visibility="collapsed")
        if session is None:
            st.warning("Warehouse session is not active. Refusals still run.")
        elif not patients:
            st.warning("The member list is empty.")
    return view, None


def member_bar(patients: list[dict[str, str | None]]) -> dict[str, str | None] | None:
    with st.container(border=True):
        choice, identity = st.columns([1.15, 1])
        with choice:
            selected = patient_selector(patients)
        with identity:
            if selected is None:
                st.caption("Choose a member to cite one chart.")
                return None
            name = f"{selected.get('first_name') or ''} {selected.get('last_name') or ''}".strip()
            place = ", ".join(part for part in (selected.get("city"), selected.get("state")) if part)
            birth = selected.get("birthdate") or "birth date not recorded"
            st.markdown(
                f'<p class="p360-member">{html.escape(name or "Selected member")}</p>'
                f'<p class="p360-member-meta">{html.escape(place or "Location not recorded")} · Born {html.escape(birth)}</p>',
                unsafe_allow_html=True,
            )
    return selected


def data_notice() -> None:
    st.caption("Synthetic Synthea members. Not real patients. Not for care.")
    with st.popover("Source and licenses"):
        st.write(BANNER)


def ask_page(
    session: object | None,
    patient_id: str | None,
    selected: dict[str, str | None] | None,
) -> None:
    del selected
    ask_heading()
    question_box(session, patient_id)


def chart_page(session: object | None, selected: dict[str, str | None] | None) -> None:
    st.markdown('<h1 class="p360-title">Member chart</h1>', unsafe_allow_html=True)
    if session is None or selected is None:
        st.info("The chart opens when the warehouse returns a member.")
        return
    patient_id = str(selected["patient_id"])
    profile(selected)
    panels = load_chart(session, patient_id)
    member_counts(panels)
    join_line(panels.get("claim_on_encounter", []))
    source_rows(panels)


def cohort_page(session: object | None) -> None:
    st.markdown('<h1 class="p360-title">Risk stratification</h1>', unsafe_allow_html=True)
    st.caption(
        "A cited point count from CORE.RISK_SCORE. "
        "This page does not train a model and does not turn the count into a probability."
    )
    risk_rows = population(session)
    cohort_audit(risk_rows)


def patient_selector(patients: list[dict[str, str | None]]) -> dict[str, str | None] | None:
    if not patients:
        return None
    labels = [_patient_label(patient) for patient in patients]
    default_index = 0
    for index, patient in enumerate(patients):
        if patient.get("patient_id") == WORKED_PATIENT_ID:
            default_index = index
            break
    choice = st.selectbox("Member", labels, index=default_index)
    return patients[labels.index(choice)]


def population(session: object | None) -> list[dict[str, str | None]]:
    if session is None:
        st.caption("Population counts wait for a warehouse session.")
        return []
    try:
        rows = fetch(session, population_query())
    except QueryFailure as exc:
        show_query_error(exc)
        rows = []
    if rows:
        row = rows[0]
        columns = st.columns(4)
        for column, label, key in (
            (columns[0], "Members", "member_count"),
            (columns[1], "Encounters", "encounter_count"),
            (columns[2], "Claims on an encounter", "claims_on_encounter"),
            (columns[3], "Documents matched to a member", "documents_matched"),
        ):
            column.metric(label, _whole(row.get(key)))
    risk_rows: list[dict[str, str | None]] = []
    try:
        risk_rows = fetch(session, risk_query())
    except QueryFailure as exc:
        show_query_error(exc)
    return risk_rows


def cohort_audit(risk_rows: list[dict[str, str | None]]) -> None:
    if not risk_rows:
        st.info("The risk count appears when CORE.RISK_SCORE returns rows.")
        return
    first = risk_rows[0]
    summary = st.columns(4)
    summary[0].metric("Cohort", _whole(first.get("cohort_n")))
    summary[1].metric("Events", _whole(first.get("event_n")))
    summary[2].metric("Base rate", _percent(first.get("base_rate")))
    summary[3].metric("Score 2 or higher", _whole(first.get("ge2_patient_count")))
    ranked = sorted(risk_rows, key=lambda row: int(float(row.get("score") or 0)))
    columns = st.columns(len(ranked))
    for column, row in zip(columns, ranked, strict=True):
        column.metric(f"Score {row.get('score')}", f"{_whole(row.get('patient_count'))} members")
        column.caption(_percent(row.get("event_rate")))
    try:
        st.bar_chart(
            {
                "Score": [str(row.get("score")) for row in ranked],
                "Members": [int(float(row.get("patient_count") or 0)) for row in ranked],
            },
            x="Score",
            y="Members",
        )
    except Exception:
        pass
    window = f"{first.get('index_date') or 'index'} through {first.get('horizon_end') or 'horizon'}"
    st.caption(f"Index window {window}. Four recorded points. Not a care recommendation.")
    with st.expander("How the four points are counted"):
        st.write(POINT_RULES)
    show_answer(
        assemble_answer(RISK_QUESTION, risk_rows=risk_rows, warehouse_connected=True),
        risk_rows,
    )


def profile(patient: dict[str, str | None]) -> None:
    columns = st.columns(4)
    fields = (
        ("Name", f"{patient.get('first_name') or ''} {patient.get('last_name') or ''}".strip()),
        ("Gender", patient.get("gender") or ""),
        ("Birth", patient.get("birthdate") or ""),
        ("Death", patient.get("deathdate") or "none"),
        ("City", patient.get("city") or ""),
        ("State", patient.get("state") or ""),
    )
    for index, (label, value) in enumerate(fields):
        columns[index % 4].metric(label, value or "blank")
    st.caption("Identifiers such as tax, license, and passport numbers are not shown.")


def load_chart(session: object, patient_id: str) -> dict[str, list[dict[str, str | None]]]:
    panels: dict[str, list[dict[str, str | None]]] = {}
    for spec in chart_queries(patient_id):
        try:
            panels[spec.name] = fetch(session, spec)
        except QueryFailure as exc:
            show_query_error(exc)
            panels[spec.name] = []
    return panels


def member_counts(panels: dict[str, list[dict[str, str | None]]]) -> None:
    encounter_total = sum(
        int(float(row["encounter_count"]))
        for row in panels.get("encounter_counts", [])
        if row.get("encounter_count")
    )
    lab_rows = panels.get("lab_count", [])
    claim_rows = panels.get("claim_count", [])
    columns = st.columns(6)
    metrics = (
        ("Encounters", str(encounter_total)),
        ("Conditions", str(len(panels.get("conditions", [])))),
        ("Medications", str(len(panels.get("medications", [])))),
        ("Labs", _whole(lab_rows[0].get("lab_count") if lab_rows else None)),
        ("Claims", _whole(claim_rows[0].get("claim_count") if claim_rows else None)),
        ("Coverage spans", str(len(panels.get("coverage", [])))),
    )
    for column, (label, value) in zip(columns, metrics, strict=True):
        column.metric(label, value)
    classes = [
        f"{row.get('encounter_class') or 'blank'} {_whole(row.get('encounter_count'))}"
        for row in panels.get("encounter_counts", [])
    ]
    if classes:
        st.caption("Encounters by class: " + ", ".join(classes) + ".")
    st.caption("A blank coverage member id stays blank. The patient id is the member key.")


def join_line(rows: list[dict[str, str | None]]) -> None:
    if not rows:
        st.info("No claim on this member has an appointment id that matches an encounter.")
        return
    row = rows[0]
    st.info(
        f"Claim {row.get('claim_id') or ''}: appointment id "
        f"{row.get('appointment_id') or ''} is encounter {row.get('encounter_id') or ''}."
    )


def source_rows(panels: dict[str, list[dict[str, str | None]]]) -> None:
    with st.expander("Source rows for this member"):
        st.caption(
            "The counts above come from these queries. "
            "Encounter lines are the latest 15. Laboratory lines are the latest 25. "
            "An empty stop, member id, or encounter id stays empty."
        )
        for name, rows in panels.items():
            st.markdown(f"**{_CHART_TITLES.get(name, name)}**")
            if name == "coverage":
                st.caption("Member id is shown as stored.")
            show_table(rows)


_PROMPT_GROUPS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "Chart",
        (
            ("Summary", MEMBER_SUMMARY_QUESTION),
            ("Conditions", CONDITION_QUESTION),
            ("Medications", MEDICATION_LIST_QUESTION),
            ("Care plans", CARE_PLAN_QUESTION),
            ("Labs", LAB_QUESTION),
            ("Claims", CLAIM_QUESTION),
        ),
    ),
    (
        "Evidence check",
        (
            ("Antihistamine", _SELECTED_ANTIHISTAMINE),
            ("Allergy guard", ALLERGY_QUESTION),
        ),
    ),
    (
        "Guardrails",
        (
            ("Dose change", DOSE_QUESTION),
            ("Discharge note", DISCHARGE_QUESTION),
            ("External label", OPENFDA_QUESTION),
            ("Treatment advice", TREATMENT_QUESTION),
        ),
    ),
)


def question_box(session: object | None, selected_patient_id: str | None) -> None:
    if "question" not in st.session_state:
        st.session_state.question = FROZEN_QUESTIONS[0]
    with st.container(border=True):
        for title, prompts in _PROMPT_GROUPS:
            st.caption(title)
            for offset in range(0, len(prompts), 3):
                row = prompts[offset : offset + 3]
                columns = st.columns(len(row))
                for column, (label, prompt) in zip(columns, row):
                    if column.button(label, key=f"prompt_{label}", use_container_width=True):
                        st.session_state.question = prompt
                        st.session_state.ask_now = True
        question = st.text_area("Question", key="question", height=110, label_visibility="collapsed")
        ask_now = st.button("Ask", type="primary", use_container_width=True) or st.session_state.pop(
            "ask_now", False
        )
    narrate = st.checkbox(
        "Optional Cortex narration (AI_COMPLETE)",
        value=False,
        help="Off by default. The cited answer does not need it. Narration sees only retrieved rows.",
    )
    model = DEFAULT_AI_COMPLETE_MODEL
    if narrate:
        model = st.text_input("AI_COMPLETE model", value=DEFAULT_AI_COMPLETE_MODEL)
    if not ask_now:
        return
    answer, rows, failure = run_question(session, question, selected_patient_id)
    if failure is not None:
        show_query_error(failure)
    show_answer(answer, rows)
    if not narrate:
        return
    if session is None or not answer.narration_allowed:
        st.caption("Narration was not run. The deterministic answer above is the demo answer.")
        return
    prompt = build_narration_prompt(question, answer, rows)
    if prompt is None:
        st.caption("Narration was not run because there is no cited row set.")
        return
    with st.expander("Bounded narration prompt"):
        st.text(prompt)
    try:
        narrated = fetch(session, QuerySpec(name="narration", sql=NARRATION_SQL, params=(model, prompt)))
    except QueryFailure as exc:
        show_query_error(exc)
        st.caption("AI_COMPLETE failed. The deterministic answer still stands.")
        return
    text = ""
    if narrated:
        text = str(narrated[0].get("narration") or "")
    if text and accept_narration(text, answer):
        st.subheader("Narration")
        st.write(text)
        return
    st.warning(
        "Cortex narration was discarded because it left the citation tuple "
        "or broke a guard. The deterministic answer stands."
    )


def run_question(
    session: object | None,
    question: str,
    selected_patient_id: str | None,
) -> tuple[Answer, list[dict[str, object]], QueryFailure | None]:
    steps = retrieval_steps(question, selected_patient_id)
    if session is None or not steps:
        answer = assemble_answer(
            question,
            selected_patient_id=selected_patient_id,
            warehouse_connected=session is not None,
        )
        return answer, [], None
    name_rows: list[dict[str, str | None]] = []
    medication_rows: list[dict[str, str | None]] = []
    section_rows: list[dict[str, str | None]] = []
    allergy_rows: list[dict[str, str | None]] = []
    risk_rows: list[dict[str, str | None]] = []
    evidence_rows: list[dict[str, str | None]] = []
    related_rows: list[dict[str, str | None]] = []
    try:
        if "patient_name" in steps:
            parsed = synthea_name(question)
            if parsed is not None:
                name_rows = fetch(session, patient_name_query(*parsed))
        patient_id = resolve_patient_id(question, selected_patient_id, name_rows)
        if "antihistamine" in steps and patient_id:
            medication_rows = fetch(session, antihistamine_query(patient_id))
        if "medication_section" in steps and patient_id and len(medication_rows) == 1:
            code = medication_rows[0].get("code")
            description = medication_rows[0].get("description")
            if code and description:
                section_rows = fetch(session, medication_section_query(patient_id, code, description))
        if "allergy" in steps and patient_id:
            allergy_rows = fetch(session, allergy_query(patient_id))
        if "allergy_section" in steps and patient_id and allergy_rows:
            section_rows = fetch(session, allergy_section_query(patient_id))
        if "risk" in steps:
            risk_rows = fetch(session, risk_query())
        if patient_id:
            for step, query in _PATIENT_EVIDENCE:
                if step in steps:
                    evidence_rows = fetch(session, query(patient_id))
            if "recent_encounters" in steps:
                related_rows = fetch(session, recent_encounter_query(patient_id))
        section_loinc = next(
            (
                loinc
                for step, loinc in (
                    ("problem_section", "11450-4"),
                    ("medication_full_section", "10160-0"),
                    ("care_plan_section", "18776-5"),
                    ("procedure_section", "47519-4"),
                    ("immunization_section", "11369-6"),
                )
                if step in steps
            ),
            None,
        )
        if section_loinc and patient_id:
            section_rows = fetch(session, document_section_query(patient_id, section_loinc))
    except QueryFailure as exc:
        answer = assemble_answer(
            question,
            selected_patient_id=selected_patient_id,
            query_failed=True,
        )
        return answer, [], exc
    answer = assemble_answer(
        question,
        selected_patient_id=selected_patient_id,
        name_rows=name_rows,
        medication_rows=medication_rows,
        section_rows=section_rows,
        allergy_rows=allergy_rows,
        risk_rows=risk_rows,
        evidence_rows=evidence_rows,
        related_rows=related_rows,
        warehouse_connected=True,
    )
    prompt_rows: list[dict[str, object]] = [
        *medication_rows,
        *allergy_rows,
        *section_rows,
        *risk_rows,
        *evidence_rows,
        *related_rows,
    ]
    return answer, prompt_rows, None


def fetch(session: object, spec: QuerySpec) -> list[dict[str, str | None]]:
    try:
        if spec.params:
            frame = session.sql(spec.sql, params=list(spec.params))  # type: ignore[attr-defined]
        else:
            frame = session.sql(spec.sql)  # type: ignore[attr-defined]
        return [normalize_row(row.as_dict()) for row in frame.collect()]
    except QueryFailure:
        raise
    except Exception as exc:
        raise QueryFailure(spec.name, str(exc)) from exc


def show_answer(answer: Answer, rows: list[dict[str, object]] | None = None) -> None:
    answer_card(answer)
    if answer.rejected_codes:
        st.warning(
            "The chart code is quoted. A different code in the same document is not quoted. "
            f"Quoted: {', '.join(answer.quoted_codes)}. "
            f"Not quoted: {', '.join(answer.rejected_codes)}."
        )
    if rows:
        with st.expander("Citation details"):
            show_table(rows)


def show_table(rows: list[dict[str, object]]) -> None:
    if not rows:
        st.caption("The query returned no rows.")
        return
    blanked = [{key: "" if value is None else value for key, value in row.items()} for row in rows]
    st.dataframe(blanked, use_container_width=True)


def show_query_error(failure: QueryFailure) -> None:
    with st.expander(f"Query failed: {failure.name}"):
        st.text(failure.detail)


def _percent(value: str | None) -> str:
    if not value:
        return "not recorded"
    return f"{float(value) * 100:.2f}%"


def _whole(value: str | None) -> str:
    if not value:
        return "0"
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return value


def _patient_label(patient: dict[str, str | None]) -> str:
    first = patient.get("first_name") or ""
    last = patient.get("last_name") or ""
    return f"{last}, {first}".strip(", ")


main()
