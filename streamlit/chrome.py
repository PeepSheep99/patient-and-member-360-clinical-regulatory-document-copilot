"""Visual shell for the Patient 360 Streamlit page."""

from __future__ import annotations

import html
import re
from pathlib import Path

import streamlit as st

from app.citations import format_citation
from app.models import (
    Answer,
    AnswerStatus,
    ClaimCitation,
    CohortCitation,
    CoverageCitation,
    DocumentCitation,
    EncounterCitation,
    ObservationCitation,
    PatientCitation,
    TableCitation,
)

MARK = Path(__file__).resolve().parent / "assets" / "patient360-mark.jpg"

_CSS = """
<style>
  .stApp {
    background: #F4F7F6;
  }
  [data-testid="stHeader"] {
    background: transparent;
  }
  [data-testid="stSidebar"] {
    background: #12312E;
  }
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] .stCaption {
    color: #E7F1EF;
  }
  .p360-brand {
    font-size: 1.15rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    margin: 0.2rem 0 0;
  }
  .p360-tag {
    color: #0E7C73;
    font-size: 0.95rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin: 0 0 0.35rem;
  }
  .p360-title {
    color: #163330;
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.15;
    margin: 0 0 0.4rem;
  }
  .p360-lead {
    color: #526864;
    font-size: 1.02rem;
    margin: 0 0 0.8rem;
  }
  .p360-card {
    background: #FFFFFF;
    border: 1px solid #D8E4E1;
    border-radius: 18px;
    padding: 1.15rem 1.25rem 0.4rem;
    margin: 0.35rem 0 1rem;
  }
  .p360-answer {
    border-radius: 18px;
    padding: 1.2rem 1.3rem 1rem;
    margin: 0.8rem 0 0.4rem;
  }
  .p360-answer.cited {
    background: #E7F5F2;
    border: 1px solid #B7DDD6;
  }
  .p360-answer.refused {
    background: #FBF3E8;
    border: 1px solid #E7D3B4;
  }
  .p360-kicker {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.45rem;
  }
  .p360-answer.cited .p360-kicker { color: #0E7C73; }
  .p360-answer.refused .p360-kicker { color: #8A5A12; }
  .p360-answer p {
    color: #1B2A28;
    font-size: 1.05rem;
    line-height: 1.45;
    margin: 0;
  }
  .p360-summary {
    font-size: 1.08rem;
    font-weight: 700;
    margin-bottom: 0.75rem;
  }
  .p360-item {
    background: #FFFFFF;
    border-radius: 14px;
    margin: 0.55rem 0;
    padding: 0.85rem 1rem 0.7rem;
  }
  .p360-name {
    color: #163330;
    font-size: 1.05rem;
    font-weight: 700;
    line-height: 1.35;
  }
  .p360-meta {
    color: #526864;
    font-size: 0.92rem;
    margin-top: 0.2rem;
  }
  .p360-source {
    border-top: 1px solid #E4EEEC;
    color: #315650;
    font-size: 0.84rem;
    line-height: 1.4;
    margin-top: 0.45rem;
    padding-top: 0.4rem;
  }
  .p360-source b {
    color: #0E7C73;
  }
  .p360-note {
    color: #526864;
    font-size: 0.9rem;
    margin-top: 0.75rem;
  }
  .p360-member {
    color: #163330;
    font-size: 1.35rem;
    font-weight: 700;
    line-height: 1.2;
    margin: 0.35rem 0 0.15rem;
  }
  .p360-member-meta {
    color: #526864;
    font-size: 0.95rem;
    margin: 0;
  }
  .p360-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-top: 0.85rem;
  }
  .p360-chip {
    background: #FFFFFF;
    border-radius: 999px;
    color: #315650;
    font-size: 0.78rem;
    padding: 0.28rem 0.65rem;
  }
  div.stButton > button {
    border-radius: 999px;
    border: 1px solid #D5E3E0;
    background: #FFFFFF;
    color: #1B2A28;
  }
  div.stButton > button[kind="primary"] {
    background: #0E7C73;
    border-color: #0E7C73;
    color: #FFFFFF;
  }
</style>
"""


def inject() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def mark(width: int = 72) -> None:
    if MARK.is_file():
        st.image(str(MARK), width=width)


def ask_heading() -> None:
    st.markdown(
        """
        <p class="p360-tag">From siloed records to evidenced answer</p>
        <h1 class="p360-title">Ask one member.</h1>
        <p class="p360-lead">The answer quotes the chart and the matching clinical document, or it refuses.</p>
        """,
        unsafe_allow_html=True,
    )


_SECTIONS = {
    "11450-4": "Problems",
    "10160-0": "Medications",
    "18776-5": "Plan of care",
    "47519-4": "Procedures",
    "11369-6": "Immunizations",
    "48765-2": "Allergies",
    "34133-9": "Summary",
}


def _clean(value: str) -> str:
    return " ".join(value.replace("\n", " ").split())


def _sentences(value: str) -> list[str]:
    return [part.strip(" .") for part in value.split(". ") if part.strip(" .")]


def _short(value: str) -> str:
    text = value.strip()
    if len(text) <= 18:
        return text or "not recorded"
    return f"{text[:8]}…{text[-4:]}"


def _fact(prose: str) -> tuple[str, str]:
    matched = re.match(
        r"^(?P<title>.*?);\s*code\s+(?P<code>[^;]+);\s*start\s+(?P<start>.+)$",
        prose,
    )
    if matched:
        return (
            matched.group("title").strip(),
            f"Code {matched.group('code').strip()} · Started {matched.group('start').strip()}",
        )
    if prose.lower().startswith("c-cda evidence:"):
        return "", prose.split(":", 1)[1].strip()
    return prose, ""


def _source(citation: object, quote: str) -> tuple[str, str]:
    if isinstance(citation, DocumentCitation):
        section = _SECTIONS.get(citation.section_loinc, citation.section_loinc)
        detail = f"{section} · {html.escape(citation.element_id)}"
        if quote:
            detail = f"{detail}<br>{html.escape(quote)}"
        return "Clinical document", detail
    if isinstance(citation, TableCitation):
        return "Chart", f"{html.escape(citation.table)} · encounter {_short(citation.encounter_id)}"
    if isinstance(citation, EncounterCitation):
        return "Encounter", f"{_short(citation.encounter_id)} · {html.escape(citation.start)}"
    if isinstance(citation, ObservationCitation):
        return "Laboratory", f"code {html.escape(citation.code)} · {html.escape(citation.observed_at)}"
    if isinstance(citation, ClaimCitation):
        return "Claim", f"{_short(citation.claim_id)} · {html.escape(citation.service_date)}"
    if isinstance(citation, CoverageCitation):
        return "Coverage", f"{html.escape(citation.payer_id)} · {html.escape(citation.start)} to {html.escape(citation.end)}"
    if isinstance(citation, PatientCitation):
        return "Member", _short(citation.patient_id)
    if isinstance(citation, CohortCitation):
        return "Cohort", f"score {html.escape(citation.score)}"
    return "Source", html.escape(format_citation(citation))


def _layout(answer: Answer) -> tuple[str, list[tuple[str, str, list[tuple[str, str]]]], str] | None:
    remaining = answer.text.strip()
    summary: list[str] = []
    notes: list[str] = []
    items: list[tuple[str, str, list[tuple[str, str]]]] = []
    for citation in answer.citations:
        token = format_citation(citation)
        before, found, remaining = remaining.partition(token)
        if not found:
            return None
        sentences = _sentences(before)
        prose = sentences[-1] if sentences else ""
        extra = sentences[:-1]
        if not items:
            summary.extend(extra)
        else:
            notes.extend(extra)
        title, meta = _fact(prose)
        quote = meta if isinstance(citation, DocumentCitation) and not title else ""
        source = _source(citation, quote)
        if isinstance(citation, DocumentCitation) and items:
            name, details, sources = items[-1]
            if not name and title:
                name = title
            sources.append(source)
            items[-1] = (name, details, sources)
            continue
        if isinstance(citation, DocumentCitation) and title:
            meta = ""
        items.append((title or "Cited record", "" if quote else meta, [source]))
    notes.extend(_sentences(remaining))
    return _finish(summary), items, _finish(notes)


def _finish(parts: list[str]) -> str:
    text = _clean(". ".join(parts))
    if text and not text.endswith("."):
        text += "."
    return text


def answer_card(answer: Answer) -> None:
    kind = "cited" if answer.status is AnswerStatus.CITED else "refused"
    label = "Cited answer" if kind == "cited" else "Refused"
    layout = _layout(answer) if answer.citations else None
    if layout is None:
        sentences = "".join(f"<p>{html.escape(part)}</p>" for part in _sentences(answer.text))
        body = sentences or f"<p>{html.escape(answer.text)}</p>"
        st.markdown(
            f'<div class="p360-answer {kind}"><div class="p360-kicker">{label}</div>{body}</div>',
            unsafe_allow_html=True,
        )
        return
    summary, items, note = layout
    rendered = []
    if summary:
        rendered.append(f'<p class="p360-summary">{html.escape(summary)}</p>')
    for title, meta, sources in items:
        source_html = "".join(
            f'<div class="p360-source"><b>{html.escape(name)}</b><br>{detail}</div>'
            for name, detail in sources
        )
        meta_html = f'<div class="p360-meta">{html.escape(meta)}</div>' if meta else ""
        rendered.append(
            f'<div class="p360-item"><div class="p360-name">{html.escape(title)}</div>'
            f"{meta_html}{source_html}</div>"
        )
    if note:
        rendered.append(f'<p class="p360-note">{html.escape(note)}</p>')
    st.markdown(
        f'<div class="p360-answer {kind}"><div class="p360-kicker">{label}</div>{"".join(rendered)}</div>',
        unsafe_allow_html=True,
    )
