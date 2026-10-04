"""Member chart laid out the way a clinician reads a record: banner, then sections."""

from __future__ import annotations

import html
from collections import Counter
from collections.abc import Callable
from datetime import date, datetime

import streamlit as st

from chrome import _pretty_when, _split_tag

Row = dict[str, str | None]
Record = dict[str, list[Row]]

_VITAL_ORDER = (
    "8480-6",
    "8462-4",
    "8867-4",
    "9279-1",
    "8310-5",
    "2708-6",
    "29463-7",
    "8302-2",
    "39156-5",
    "72514-3",
)
_CATEGORY_TITLES = {
    "vital-signs": "Vital signs",
    "laboratory": "Laboratory",
    "social-history": "Social history",
    "survey": "Questionnaires and scores",
    "exam": "Examination findings",
    "imaging": "Imaging observations",
    "procedure": "Procedure observations",
    "therapy": "Therapy observations",
}


def render(selected: Row, record: Record) -> None:
    _banner(selected, record)
    tabs = st.tabs(
        (
            "Summary",
            f"Problems ({len(record.get('record_problems', []))})",
            f"Medications ({len(record.get('record_medications', []))})",
            "Results",
            f"Immunizations ({len(record.get('record_immunizations', []))})",
            f"Care plans ({len(record.get('record_careplans', []))})",
            f"Procedures ({len(record.get('record_procedures', []))})",
            f"Encounters ({len(record.get('record_encounters', []))})",
            "Coverage and claims",
            "Devices and imaging",
        )
    )
    sections: tuple[Callable[[Record], None], ...] = (
        _summary,
        _problems,
        _medications,
        _results,
        _immunizations,
        _careplans,
        _procedures,
        _encounters,
        _coverage_claims,
        _devices_imaging,
    )
    for tab, section in zip(tabs, sections, strict=True):
        with tab:
            section(record)


def _banner(selected: Row, record: Record) -> None:
    name = f"{selected.get('first_name') or ''} {selected.get('last_name') or ''}".strip()
    birth = selected.get("birthdate") or ""
    death = selected.get("deathdate")
    gender = {"F": "Female", "M": "Male"}.get(selected.get("gender") or "", selected.get("gender") or "")
    age = _age(birth, death)
    identity = " · ".join(
        part
        for part in (
            gender,
            f"{age} years" if age is not None else "",
            f"Born {_pretty_when(birth)}" if birth else "",
            ", ".join(p for p in (selected.get("city"), selected.get("state")) if p),
        )
        if part
    )
    allergies = record.get("record_allergies", [])
    if allergies:
        names = ", ".join(_split_tag(row.get("description") or "")[0] for row in allergies)
        allergy_chip = f'<span class="p360-chip alert">Allergies · {html.escape(names)}</span>'
    else:
        allergy_chip = '<span class="p360-chip">No allergy recorded</span>'
    active_problems = [r for r in record.get("record_problems", []) if not r.get("stop_date")]
    active_meds = [r for r in record.get("record_medications", []) if not r.get("stop_ts")]
    chips = [
        allergy_chip,
        f'<span class="p360-chip">{_count(len(active_problems), "active problem")}</span>',
        f'<span class="p360-chip">{_count(len(active_meds), "active medication")}</span>',
    ]
    encounters = record.get("record_encounters", [])
    if encounters:
        last = encounters[0]
        chips.append(
            f'<span class="p360-chip">Last visit {html.escape(_day(last.get("start_ts")))} · '
            f'{html.escape((last.get("encounter_class") or "").capitalize())}</span>'
        )
    coverage = record.get("record_coverage", [])
    if coverage:
        chips.append(f'<span class="p360-chip">Coverage · {html.escape(coverage[0].get("payer_name") or "")}</span>')
    deceased = (
        f'<span class="p360-chip alert">Deceased {html.escape(_pretty_when(death))}</span>' if death else ""
    )
    st.markdown(
        f'<div class="p360-banner"><div class="p360-banner-name">{html.escape(name)}{deceased}</div>'
        f'<div class="p360-banner-meta">{html.escape(identity)}</div>'
        f'<div class="p360-chips">{"".join(chips)}</div></div>',
        unsafe_allow_html=True,
    )


def _summary(record: Record) -> None:
    left, right = st.columns(2, gap="large")
    with left:
        _card(
            "Allergies",
            [
                (
                    _split_tag(row.get("description") or "")[0],
                    _join(
                        (row.get("category") or "").capitalize(),
                        _reaction(row),
                        f"Recorded {_day(row.get('start_date'))}",
                    ),
                )
                for row in record.get("record_allergies", [])
            ],
            "No allergy is recorded on this chart.",
        )
        _card(
            "Active problems",
            [
                (_split_tag(row.get("description") or "")[0], f"Since {_day(row.get('start_date'))}")
                for row in record.get("record_problems", [])
                if not row.get("stop_date")
            ],
            "No active problem is recorded.",
        )
        _card(
            "Active medications",
            [
                (row.get("description") or "", _join(f"Since {_day(row.get('start_ts'))}", _for(row)))
                for row in record.get("record_medications", [])
                if not row.get("stop_ts")
            ],
            "No active medication is recorded.",
        )
    with right:
        _vitals_grid(record)
        _card(
            "Recent encounters",
            [
                (
                    row.get("description") or "",
                    _join(
                        _day(row.get("start_ts")),
                        (row.get("encounter_class") or "").capitalize(),
                        _title(row.get("organization_name")),
                    ),
                )
                for row in record.get("record_encounters", [])[:5]
            ],
            "No encounter is recorded.",
        )
        _card(
            "Active care plans",
            [
                (row.get("description") or "", _join(f"Since {_day(row.get('start_date'))}", _for(row)))
                for row in record.get("record_careplans", [])
                if not row.get("stop_date")
            ],
            "No active care plan is recorded.",
        )
        _card(
            "Recent immunizations",
            [
                (row.get("description") or "", _day(row.get("immunization_ts")))
                for row in record.get("record_immunizations", [])[:4]
            ],
            "No immunization is recorded.",
        )


def _problems(record: Record) -> None:
    rows = record.get("record_problems", [])
    active = [r for r in rows if not r.get("stop_date")]
    resolved = [r for r in rows if r.get("stop_date")]
    _table(
        f"Active ({len(active)})",
        [
            {
                "Problem": _split_tag(r.get("description") or "")[0],
                "Type": _split_tag(r.get("description") or "")[1].capitalize(),
                "Onset": _day(r.get("start_date")),
                "SNOMED code": r.get("code") or "",
            }
            for r in active
        ],
    )
    _table(
        f"Resolved ({len(resolved)})",
        [
            {
                "Problem": _split_tag(r.get("description") or "")[0],
                "Type": _split_tag(r.get("description") or "")[1].capitalize(),
                "Onset": _day(r.get("start_date")),
                "Resolved": _day(r.get("stop_date")),
                "SNOMED code": r.get("code") or "",
            }
            for r in resolved
        ],
    )


def _medications(record: Record) -> None:
    rows = record.get("record_medications", [])
    active = [r for r in rows if not r.get("stop_ts")]
    past = [r for r in rows if r.get("stop_ts")]
    _table(
        f"Active ({len(active)})",
        [
            {
                "Medication": r.get("description") or "",
                "Started": _day(r.get("start_ts")),
                "Reason": r.get("reason_description") or "",
                "Dispenses": _whole(r.get("dispenses")),
                "RxNorm code": r.get("code") or "",
            }
            for r in active
        ],
    )
    _table(
        f"Past ({len(past)})",
        [
            {
                "Medication": r.get("description") or "",
                "Started": _day(r.get("start_ts")),
                "Stopped": _day(r.get("stop_ts")),
                "Reason": r.get("reason_description") or "",
                "Dispenses": _whole(r.get("dispenses")),
                "RxNorm code": r.get("code") or "",
            }
            for r in past
        ],
    )


def _results(record: Record) -> None:
    rows = record.get("record_observations", [])
    if not rows:
        st.caption("No observation is recorded.")
        return
    st.caption("Latest value for each test, with the reading before it.")
    grouped: dict[str, list[Row]] = {}
    for row in rows:
        grouped.setdefault(row.get("category") or "other", []).append(row)
    order = [c for c in _CATEGORY_TITLES if c in grouped] + [c for c in grouped if c not in _CATEGORY_TITLES]
    for category in order:
        _table(
            f"{_CATEGORY_TITLES.get(category, category.capitalize())} ({len(grouped[category])})",
            [
                {
                    "Test": r.get("description") or "",
                    "Latest": _value(r.get("value_text"), r.get("units")),
                    "Date": _day(r.get("observation_ts")),
                    "Previous": _value(r.get("previous_value"), r.get("units")) if r.get("previous_value") else "",
                    "Trend": _trend(r.get("value_text"), r.get("previous_value")),
                    "Readings": _whole(r.get("readings")),
                }
                for r in grouped[category]
            ],
        )


def _immunizations(record: Record) -> None:
    _table(
        "",
        [
            {"Vaccine": r.get("description") or "", "Given": _day(r.get("immunization_ts")), "CVX code": r.get("code") or ""}
            for r in record.get("record_immunizations", [])
        ],
    )


def _careplans(record: Record) -> None:
    _table(
        "",
        [
            {
                "Care plan": r.get("description") or "",
                "Status": "Active" if not r.get("stop_date") else "Completed",
                "Started": _day(r.get("start_date")),
                "Ended": _day(r.get("stop_date")) if r.get("stop_date") else "",
                "For": r.get("reason_description") or "",
            }
            for r in record.get("record_careplans", [])
        ],
    )


def _procedures(record: Record) -> None:
    _table(
        "",
        [
            {
                "Procedure": _split_tag(r.get("description") or "")[0],
                "Date": _day(r.get("start_ts")),
                "Reason": r.get("reason_description") or "",
                "SNOMED code": r.get("code") or "",
            }
            for r in record.get("record_procedures", [])
        ],
    )


def _encounters(record: Record) -> None:
    rows = record.get("record_encounters", [])
    classes = Counter((r.get("encounter_class") or "blank").capitalize() for r in rows)
    if classes:
        st.caption("By class: " + ", ".join(f"{name} {count}" for name, count in classes.most_common()) + ".")
    _table(
        "",
        [
            {
                "Date": _pretty_when(r.get("start_ts") or ""),
                "Class": (r.get("encounter_class") or "").capitalize(),
                "Visit": r.get("description") or "",
                "Reason": r.get("reason_description") or "",
                "Facility": _title(r.get("organization_name")),
                "Clinician": r.get("provider_name") or "",
                "Specialty": _title(r.get("speciality")),
            }
            for r in rows
        ],
    )


def _coverage_claims(record: Record) -> None:
    _table(
        f"Coverage ({len(record.get('record_coverage', []))})",
        [
            {
                "Payer": r.get("payer_name") or "",
                "From": _day(r.get("start_ts")),
                "To": _day(r.get("end_ts")),
                "Plan owner": (r.get("plan_ownership") or "").capitalize(),
                "Member id": r.get("member_id") or "",
            }
            for r in record.get("record_coverage", [])
        ],
    )
    st.caption("A blank member id stays blank. The patient id is the member key.")
    _table(
        f"Claims ({len(record.get('record_claims', []))})",
        [
            {
                "Service date": _day(r.get("service_ts")),
                "Visit": r.get("encounter_description") or "Not tied to an encounter",
                "Class": (r.get("encounter_class") or "").capitalize(),
                "Billed": _money(r.get("total_claim_cost")),
                "Payer paid": _money(r.get("payer_coverage")),
                "Claim": r.get("claim_id") or "",
            }
            for r in record.get("record_claims", [])
        ],
    )
    st.caption("Each claim is joined to the encounter whose id equals the claim appointment id.")


def _devices_imaging(record: Record) -> None:
    _table(
        f"Devices ({len(record.get('record_devices', []))})",
        [
            {
                "Device": _split_tag(r.get("description") or "")[0],
                "Since": _day(r.get("start_ts")),
                "Until": _day(r.get("stop_ts")) if r.get("stop_ts") else "In use",
                "SNOMED code": r.get("code") or "",
            }
            for r in record.get("record_devices", [])
        ],
    )
    _table(
        f"Imaging studies ({len(record.get('record_imaging', []))})",
        [
            {
                "Date": _day(r.get("imaging_ts")),
                "Modality": r.get("modality_description") or "",
                "Body site": r.get("body_site_description") or "",
            }
            for r in record.get("record_imaging", [])
        ],
    )


def _vitals_grid(record: Record) -> None:
    vitals = {r.get("code"): r for r in record.get("record_observations", []) if r.get("category") == "vital-signs"}
    if not vitals:
        _card("Latest vitals", [], "No vital sign is recorded.")
        return
    cells: list[tuple[str, str, str]] = []
    systolic, diastolic = vitals.get("8480-6"), vitals.get("8462-4")
    if systolic and diastolic:
        cells.append(("Blood pressure", f"{_num(systolic.get('value_text'))}/{_num(diastolic.get('value_text'))} mm[Hg]", _day(systolic.get("observation_ts"))))
    for code in _VITAL_ORDER[2:]:
        row = vitals.get(code)
        if row:
            cells.append((_short_vital(row.get("description") or ""), _value(row.get("value_text"), row.get("units")), _day(row.get("observation_ts"))))
    for code, row in vitals.items():
        if code not in _VITAL_ORDER:
            cells.append((_short_vital(row.get("description") or ""), _value(row.get("value_text"), row.get("units")), _day(row.get("observation_ts"))))
    body = "".join(
        f'<div class="p360-vital"><div class="p360-vital-label">{html.escape(label)}</div>'
        f'<div class="p360-vital-value">{html.escape(value)}</div>'
        f'<div class="p360-vital-when">{html.escape(when)}</div></div>'
        for label, value, when in cells
    )
    st.markdown(
        f'<div class="p360-card"><div class="p360-card-title">Latest vitals</div><div class="p360-vitals">{body}</div></div>',
        unsafe_allow_html=True,
    )


def _card(title: str, items: list[tuple[str, str]], empty: str) -> None:
    if items:
        body = "".join(
            f'<li><div class="p360-card-item">{html.escape(name)}</div>'
            + (f'<div class="p360-card-sub">{html.escape(sub)}</div>' if sub else "")
            + "</li>"
            for name, sub in items
        )
        body = f'<ul class="p360-card-list">{body}</ul>'
    else:
        body = f'<p class="p360-card-empty">{html.escape(empty)}</p>'
    count = f' <span class="p360-card-count">{len(items)}</span>' if items else ""
    st.markdown(
        f'<div class="p360-card"><div class="p360-card-title">{html.escape(title)}{count}</div>{body}</div>',
        unsafe_allow_html=True,
    )


def _table(title: str, rows: list[dict[str, str]]) -> None:
    if title:
        st.markdown(f"**{title}**")
    if not rows:
        st.caption("Nothing recorded.")
        return
    st.dataframe(rows, use_container_width=True, hide_index=True, height=min(38 + 35 * len(rows), 560))


def _age(birth: str, death: str | None) -> int | None:
    try:
        born = datetime.strptime(birth[:10], "%Y-%m-%d").date()
        end = datetime.strptime(death[:10], "%Y-%m-%d").date() if death else date.today()
    except ValueError:
        return None
    return end.year - born.year - ((end.month, end.day) < (born.month, born.day))


def _day(value: str | None) -> str:
    if not value:
        return ""
    return _pretty_when(value[:10])


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}{'' if number == 1 else 's'}"


def _join(*parts: str) -> str:
    return " · ".join(part for part in parts if part)


def _for(row: Row) -> str:
    reason = row.get("reason_description")
    return f"For {_split_tag(reason)[0].lower()}" if reason else ""


def _reaction(row: Row) -> str:
    reactions = []
    for index in (1, 2):
        what = row.get(f"reaction_{index}_description")
        if what:
            severity = row.get(f"reaction_{index}_severity")
            reactions.append(f"{_split_tag(what)[0]}{f' ({severity.lower()})' if severity else ''}")
    return "Reaction: " + ", ".join(reactions) if reactions else ""


def _title(value: str | None) -> str:
    if not value:
        return ""
    return value if not value.isupper() else value.title()


def _num(value: str | None) -> str:
    if value is None:
        return ""
    try:
        number = float(value)
    except ValueError:
        return value
    return str(int(number)) if number.is_integer() else f"{number:.1f}"


def _value(value: str | None, units: str | None) -> str:
    if value is None:
        return ""
    shown = _num(value)
    return f"{shown} {units}".strip() if units else shown


def _trend(latest: str | None, previous: str | None) -> str:
    try:
        now, before = float(latest or ""), float(previous or "")
    except ValueError:
        return ""
    if abs(now - before) < 1e-9:
        return "→ same"
    return "↑ up" if now > before else "↓ down"


def _whole(value: str | None) -> str:
    if not value:
        return ""
    return _num(value)


def _money(value: str | None) -> str:
    if not value:
        return ""
    try:
        return f"${float(value):,.2f}"
    except ValueError:
        return value


def _short_vital(description: str) -> str:
    replacements = {
        "Body Height": "Height",
        "Body Weight": "Weight",
        "Body mass index (BMI) [Ratio]": "BMI",
        "Heart rate": "Heart rate",
        "Respiratory rate": "Respiratory rate",
        "Body temperature": "Temperature",
        "Oxygen saturation in Arterial blood": "Oxygen saturation",
        "Pain severity - 0-10 verbal numeric rating [Score] - Reported": "Pain (0-10)",
    }
    return replacements.get(description, description)
