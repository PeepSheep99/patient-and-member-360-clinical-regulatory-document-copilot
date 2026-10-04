"""Visual shell for the Patient 360 Streamlit page."""

from __future__ import annotations

import html
import re
from datetime import datetime
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
    Intent,
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
  [data-testid="stSidebar"] {
    min-width: 19rem;
  }
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] .stCaption {
    color: #E7F1EF;
  }
  [data-testid="stSidebar"] [data-testid="stRadio"] label p {
    font-size: 1.05rem;
    font-weight: 650;
    line-height: 1.35;
  }
  [data-testid="stSidebar"] [data-testid="stRadio"] label {
    margin-bottom: 0.35rem;
  }
  [data-testid="stSidebar"] .p360-side-name {
    color: #FFFFFF;
    font-size: 1.2rem;
    font-weight: 750;
    line-height: 1.25;
    margin: 0.8rem 0 0.15rem;
  }
  [data-testid="stSidebar"] .p360-side-meta {
    color: #D5ECE8;
    font-size: 0.92rem;
    margin: 0.1rem 0;
  }
  [data-testid="stSidebar"] .p360-side-alert {
    color: #F6D9D2;
    font-size: 0.92rem;
    font-weight: 650;
    margin: 0.45rem 0 0.1rem;
  }
  [data-testid="stSidebar"] .p360-side-kicker {
    color: #8FBFB8;
    font-size: 0.75rem;
    font-weight: 750;
    letter-spacing: 0.08em;
    margin: 1rem 0 0.35rem;
    text-transform: uppercase;
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
  [data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 0.15rem;
  }
  [data-testid="stTabs"] button[data-baseweb="tab"] {
    height: auto;
    padding: 0.85rem 1.15rem;
  }
  [data-testid="stTabs"] button[data-baseweb="tab"] p {
    font-size: 1.08rem;
    font-weight: 650;
    line-height: 1.2;
  }
  [data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    background-color: #0E7C73;
    height: 3px;
  }
  [data-testid="stTabs"] [data-baseweb="tab-border"] {
    background-color: #D5E4E1;
  }
  .p360-tabline {
    color: #526864;
    font-size: 0.98rem;
    margin: 0.15rem 0 0.85rem;
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
  .p360-prose {
    color: #1B2A28;
    font-size: 1.05rem;
    line-height: 1.55;
    margin: 0 0 0.75rem;
  }
  .p360-timeline {
    margin: 0 0 0.4rem;
    padding-left: 1.15rem;
  }
  .p360-timeline li {
    color: #1B2A28;
    line-height: 1.45;
    margin: 0.38rem 0;
  }
  .p360-when {
    color: #0E7C73;
    font-weight: 700;
  }
  .p360-banner {
    background: linear-gradient(135deg, #12312E 0%, #0E7C73 100%);
    border-radius: 18px;
    color: #FFFFFF;
    margin: 0.4rem 0 1rem;
    padding: 1.2rem 1.4rem;
  }
  .p360-banner-name {
    font-size: 1.7rem;
    font-weight: 800;
    letter-spacing: -0.01em;
  }
  .p360-banner-meta {
    color: #D5ECE8;
    font-size: 0.98rem;
    margin-top: 0.2rem;
  }
  .p360-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    margin-top: 0.8rem;
  }
  .p360-chip {
    background: rgba(255, 255, 255, 0.14);
    border-radius: 999px;
    color: #FFFFFF;
    font-size: 0.82rem;
    font-weight: 600;
    margin-left: 0.4rem;
    padding: 0.25rem 0.7rem;
  }
  .p360-chips .p360-chip {
    margin-left: 0;
  }
  .p360-chip.alert {
    background: #F6D9D2;
    color: #8A2A14;
  }
  .p360-card {
    background: #FFFFFF;
    border: 1px solid #E1EAE8;
    border-radius: 14px;
    margin-bottom: 0.9rem;
    padding: 0.9rem 1rem;
  }
  .p360-card-title {
    color: #0E7C73;
    font-size: 0.8rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    margin-bottom: 0.4rem;
    text-transform: uppercase;
  }
  .p360-card-count {
    background: #E6F2EF;
    border-radius: 999px;
    color: #0E7C73;
    margin-left: 0.3rem;
    padding: 0.05rem 0.45rem;
  }
  .p360-card-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .p360-card-list li {
    border-top: 1px solid #EEF3F2;
    padding: 0.45rem 0;
  }
  .p360-card-list li:first-child {
    border-top: none;
  }
  .p360-card-item {
    color: #1B2A28;
    font-weight: 600;
  }
  .p360-card-sub,
  .p360-card-empty {
    color: #61736F;
    font-size: 0.86rem;
  }
  .p360-vitals {
    display: grid;
    gap: 0.6rem;
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  }
  .p360-vital {
    background: #F4F7F6;
    border-radius: 10px;
    padding: 0.55rem 0.7rem;
  }
  .p360-vital-label,
  .p360-vital-when {
    color: #61736F;
    font-size: 0.76rem;
  }
  .p360-vital-value {
    color: #1B2A28;
    font-size: 1.05rem;
    font-weight: 700;
  }
  .p360-prose.small {
    color: #526864;
    font-size: 0.92rem;
    margin: 0.4rem 0 0.6rem;
  }
  .p360-name.big {
    font-size: 1.3rem;
  }
  .p360-list {
    margin: 0;
    padding-left: 1.3rem;
  }
  .p360-list li {
    background: #FFFFFF;
    border-radius: 12px;
    margin: 0.5rem 0;
    padding: 0.7rem 0.9rem;
  }
  .p360-list li::marker {
    color: #0E7C73;
    font-weight: 700;
  }
  .p360-tag-pill {
    background: #E6EEEC;
    border-radius: 999px;
    color: #315650;
    font-size: 0.72rem;
    font-weight: 600;
    margin-left: 0.4rem;
    padding: 0.12rem 0.5rem;
    vertical-align: middle;
  }
  .p360-doc {
    color: #6A7C79;
    font-size: 0.86rem;
    margin-top: 0.35rem;
  }
  .p360-doc.ok {
    color: #0E6B63;
  }
  .p360-doc.ok::before {
    content: "✓ ";
    font-weight: 700;
  }
  .p360-guard {
    background: #FBF3E8;
    border-radius: 10px;
    color: #7A4F0E;
    font-size: 0.9rem;
    margin-top: 0.6rem;
    padding: 0.55rem 0.75rem;
  }
  .p360-table {
    background: #FFFFFF;
    border-collapse: collapse;
    border-radius: 12px;
    font-size: 0.93rem;
    overflow: hidden;
    width: 100%;
  }
  .p360-table th {
    background: #DDEDE9;
    color: #163330;
    font-weight: 700;
    padding: 0.55rem 0.75rem;
    text-align: left;
  }
  .p360-table td {
    border-top: 1px solid #E8F0EE;
    color: #1B2A28;
    padding: 0.5rem 0.75rem;
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


def _pretty_when(value: str) -> str:
    text = value.replace("T", " ").replace("Z", "").strip()
    parsed = None
    for fmt, size in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d", 10)):
        try:
            parsed = datetime.strptime(text[:size], fmt)
            break
        except ValueError:
            continue
    if parsed is None:
        return value
    clock = parsed.strftime("%H:%M")
    date = f"{parsed.day} {parsed.strftime('%b %Y')}"
    if clock == "00:00" and len(text) <= 10:
        return date
    return f"{date}, {clock}"


def _member_narrative(answer: Answer) -> str | None:
    if not answer.citations or not isinstance(answer.citations[0], PatientCitation):
        return None
    if any(not isinstance(citation, EncounterCitation) for citation in answer.citations[1:]):
        return None
    remaining = answer.text.strip()
    pieces: list[str] = []
    for citation in answer.citations:
        token = format_citation(citation)
        before, found, remaining = remaining.partition(token)
        if not found:
            return None
        sentences = _sentences(before)
        pieces.append(sentences[-1] if sentences else "")
    identity = re.match(
        r"^(?P<name>.+?): gender (?P<gender>.+?), birth (?P<birth>.+?), "
        r"city/state (?P<city>.+?)/(?P<state>.+)$",
        pieces[0],
    )
    if identity is None:
        return None
    gender = {"f": "female", "m": "male"}.get(identity.group("gender").strip().lower(), identity.group("gender"))
    intro = (
        f"<p class=\"p360-prose\"><b>{html.escape(identity.group('name'))}</b> is recorded as "
        f"{html.escape(gender)}, born {_pretty_when(identity.group('birth'))}, in "
        f"{html.escape(identity.group('city'))}, {html.escape(identity.group('state'))}.</p>"
    )
    items: list[str] = []
    for prose in pieces[1:]:
        matched = re.match(r"^Encounter (?P<kind>\S+) on (?P<rest>.+)$", prose)
        if matched is None or ": " not in matched.group("rest"):
            return None
        when, what = matched.group("rest").split(": ", 1)
        kind = matched.group("kind").strip().capitalize()
        what = re.sub(r"\s*\(procedure\)\s*$", "", what.strip(), flags=re.IGNORECASE)
        items.append(
            "<li><span class=\"p360-when\">"
            f"{html.escape(_pretty_when(when))}</span> · {html.escape(kind)} · {html.escape(what)}</li>"
        )
    encounters = (
        "<p class=\"p360-prose\">Recent encounters on the chart:</p>"
        f"<ul class=\"p360-timeline\">{''.join(items)}</ul>"
        if items
        else "<p class=\"p360-prose\">No recent encounters were retrieved.</p>"
    )
    note = _finish(_sentences(remaining))
    note_html = f"<p class=\"p360-note\">{html.escape(note)}</p>" if note else ""
    return intro + encounters + note_html


_LIST_LABELS = {
    Intent.CONDITION_LIST: ("Conditions", "Recorded"),
    Intent.MEDICATION_LIST: ("Medications", "Started"),
    Intent.CARE_PLAN_LIST: ("Care plans", "Started"),
    Intent.PROCEDURE_LIST: ("Procedures", "Performed"),
    Intent.IMMUNIZATION_LIST: ("Immunizations", "Given"),
}


def _segments(answer: Answer) -> tuple[list[str], str] | None:
    remaining = answer.text.strip()
    before: list[str] = []
    for citation in answer.citations:
        head, found, remaining = remaining.partition(format_citation(citation))
        if not found:
            return None
        before.append(head)
    return before, remaining


def _split_tag(value: str) -> tuple[str, str]:
    matched = re.match(r"^(?P<name>.+?)\s*\((?P<tag>[^()]+)\)$", value.strip())
    if matched is None:
        return value.strip(), ""
    return matched.group("name").strip(), matched.group("tag").strip()


def _readable_quote(text: str, title: str) -> str:
    quote = text.strip().rstrip(".")
    if not quote or quote.lower().startswith("http") or quote.lower() == title.lower():
        return ""
    return quote


def _note_html(sentences: list[str]) -> str:
    note = _finish(sentences)
    return f'<p class="p360-note">{html.escape(note)}</p>' if note else ""


def _table_html(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    head = "".join(f"<th>{html.escape(cell)}</th>" for cell in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in row) + "</tr>" for row in rows
    )
    return f'<table class="p360-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def _shown_line(header: list[str], fallback: str) -> str:
    for sentence in header:
        matched = re.search(r"(\d+)\s+(?:retrieved\s+)?(?:rows|spans)", sentence)
        if matched:
            return f"{fallback} · showing {matched.group(1)} retrieved"
    return fallback


def _clinical_list(answer: Answer) -> str | None:
    labels = _LIST_LABELS.get(answer.intent)
    split = _segments(answer)
    if labels is None or split is None:
        return None
    noun, verb = labels
    before, tail = split
    header: list[str] = []
    items: list[dict[str, object]] = []
    for citation, segment in zip(answer.citations, before, strict=True):
        sentences = _sentences(segment)
        prose = sentences[-1] if sentences else ""
        if isinstance(citation, DocumentCitation):
            if not items:
                return None
            quote = prose.split(":", 1)[1] if prose.lower().startswith("c-cda evidence:") else ""
            items[-1]["documents"].append(  # type: ignore[union-attr]
                (_SECTIONS.get(citation.section_loinc, citation.section_loinc), quote)
            )
            continue
        if not items:
            header.extend(sentences[:-1])
        matched = re.match(
            r"^(?P<title>.*?);\s*code\s+(?P<code>[^;]+);\s*start\s+(?P<start>.+)$", prose
        )
        if matched is None:
            return None
        items.append(
            {
                "title": matched.group("title"),
                "code": matched.group("code").strip(),
                "start": matched.group("start").strip(),
                "documents": [],
            }
        )
    rendered: list[str] = []
    for item in items:
        name, tag = _split_tag(str(item["title"]))
        tag_html = f' <span class="p360-tag-pill">{html.escape(tag)}</span>' if tag else ""
        documents = item["documents"]
        if documents:
            sections = sorted({section for section, _ in documents})  # type: ignore[union-attr]
            quotes = [
                _readable_quote(quote, str(item["title"]))
                for _, quote in documents  # type: ignore[union-attr]
            ]
            quotes = [quote for quote in quotes if quote]
            quote_html = f" · “{html.escape(quotes[0])}”" if quotes else ""
            evidence = (
                f'<div class="p360-doc ok">Also written in the clinical document · '
                f"{html.escape(', '.join(sections))} section{quote_html}</div>"
            )
        else:
            evidence = '<div class="p360-doc">Chart record only. No matching document cell was retrieved.</div>'
        rendered.append(
            f'<li><div class="p360-name">{html.escape(name)}{tag_html}</div>'
            f'<div class="p360-meta">{verb} {html.escape(_pretty_when(str(item["start"])))}'
            f" · Code {html.escape(str(item['code']))}</div>{evidence}</li>"
        )
    return (
        f'<p class="p360-summary">{html.escape(_shown_line(header, noun))}</p>'
        f'<ol class="p360-list">{"".join(rendered)}</ol>'
        + _note_html(_sentences(tail))
    )


def _row_table(answer: Answer) -> str | None:
    patterns = {
        Intent.LAB_RESULTS: (
            r"^(?P<a>.+?): (?P<b>.+?) on (?P<c>.+)$",
            ("Test", "Result", "Date"),
            "Latest laboratory results",
        ),
        Intent.CLAIM_ENCOUNTER: (
            r"^Claim (?P<a>\S+) is tied to encounter (?P<b>\S+) on (?P<c>.+?); class (?P<d>.+)$",
            ("Service date", "Encounter class", "Claim", "Encounter"),
            "Claims tied to encounters",
        ),
        Intent.COVERAGE_LIST: (
            r"^(?P<a>.+?) from (?P<b>.+?) to (?P<c>.+?); member id (?P<d>.+)$",
            ("Payer", "From", "To", "Member id"),
            "Coverage spans",
        ),
    }
    spec = patterns.get(answer.intent)
    split = _segments(answer)
    if spec is None or split is None:
        return None
    pattern, headers, title = spec
    before, tail = split
    header: list[str] = []
    rows: list[tuple[str, ...]] = []
    for index, segment in enumerate(before):
        sentences = _sentences(segment)
        if index == 0:
            header.extend(sentences[:-1])
        matched = re.match(pattern, sentences[-1] if sentences else "")
        if matched is None:
            return None
        parts = matched.groupdict()
        if answer.intent is Intent.LAB_RESULTS:
            rows.append((parts["a"], " ".join(parts["b"].split()), _pretty_when(parts["c"])))
        elif answer.intent is Intent.CLAIM_ENCOUNTER:
            rows.append(
                (_pretty_when(parts["c"]), parts["d"].capitalize(), _short(parts["a"]), _short(parts["b"]))
            )
        else:
            rows.append((parts["a"], _pretty_when(parts["b"]), _pretty_when(parts["c"]), parts["d"]))
    return (
        f'<p class="p360-summary">{html.escape(_shown_line(header, title))}</p>'
        + _table_html(headers, rows)
        + _note_html(_sentences(tail))
    )


def _evidence_check(answer: Answer) -> str | None:
    if answer.intent not in (Intent.MEDICATION_CITATION, Intent.ALLERGY_CITATION):
        return None
    split = _segments(answer)
    if split is None or not answer.citations:
        return None
    before, tail = split
    chunks = [*before[1:], tail]
    documents: list[tuple[str, str]] = []
    leftovers: list[str] = []
    for index, chunk in enumerate(chunks):
        sentences = _sentences(chunk)
        texts = [s.split(":", 1)[1].strip() for s in sentences if s.startswith("Section text:")]
        leftovers.extend(s for s in sentences if not s.startswith("Section text:"))
        if index < len(answer.citations) - 1:
            citation = answer.citations[index + 1]
            if isinstance(citation, DocumentCitation):
                section = _SECTIONS.get(citation.section_loinc, citation.section_loinc)
                documents.append((section, texts[0] if texts else ""))
        elif texts and documents:
            section, _old = documents[-1]
            documents[-1] = (section, texts[0])
    lead = _sentences(before[0])
    guards = [s for s in leftovers if s.startswith("Not the quoted allergy")]
    notes = [s for s in leftovers if s not in guards]
    if answer.intent is Intent.ALLERGY_CITATION:
        matched = re.match(r"^Quoted allergy code (?P<code>\S+), (?P<desc>.+)$", lead[0] if lead else "")
        if matched is None:
            return None
        title, tag = _split_tag(matched.group("desc"))
        facts = [f"Quoted code {matched.group('code')}"]
        for sentence in lead[1:]:
            if sentence.startswith("Start "):
                facts.append(f"Recorded {_pretty_when(sentence[6:])}")
        explain = "The quoted code is the code on the chart allergy row."
        heading = "Allergy on the chart"
    else:
        matched = re.match(r"^(?:(?P<who>.+?): )?(?P<desc>.+?) is on the retrieved medication list$", lead[0] if lead else "")
        if matched is None:
            return None
        title, tag = _split_tag(matched.group("desc"))
        facts = []
        for sentence in lead[1:]:
            if sentence.startswith("Code "):
                facts.append(sentence)
            elif sentence.startswith("Start "):
                facts.append(f"Started {_pretty_when(sentence[6:])}")
        explain = "One medication row matched. The page does not choose between rows."
        heading = "Medication on the chart"
    tag_html = f' <span class="p360-tag-pill">{html.escape(tag)}</span>' if tag else ""
    documents = list(dict.fromkeys((section, _readable_quote(text, title)) for section, text in documents))
    rejected = [
        found.group(1)
        for guard in guards
        if (found := re.search(r"retrieved code (\S+) differs", guard)) is not None
    ]
    if rejected:
        guards = [
            f"Not quoted: the same document entry also carries {', '.join(rejected)}. "
            "Those are different concepts from the chart code, so they are shown here and not cited"
        ]
    doc_html = "".join(
        f'<div class="p360-doc ok">{html.escape(section)} section'
        + (f" · “{html.escape(_readable_quote(text, title))}”" if _readable_quote(text, title) else "")
        + "</div>"
        for section, text in documents
    ) or '<div class="p360-doc">No matching document cell was retrieved, so none is claimed.</div>'
    guard_html = "".join(f'<div class="p360-guard">{html.escape(g)}.</div>' for g in guards)
    return (
        f'<p class="p360-tag">{heading}</p>'
        f'<div class="p360-name big">{html.escape(title)}{tag_html}</div>'
        f'<div class="p360-meta">{html.escape(" · ".join(facts))}</div>'
        f'<p class="p360-prose small">{html.escape(explain)}</p>'
        f'<p class="p360-summary">Where it is written</p>'
        f'<div class="p360-doc ok">Chart · {html.escape("ALLERGY" if answer.intent is Intent.ALLERGY_CITATION else "MEDICATION")} table</div>'
        f"{doc_html}{guard_html}"
        + _note_html(
            [n for n in notes if not n.startswith("The quoted code is the allergies.csv code")]
        )
    )


def _risk_answer(answer: Answer) -> str | None:
    if answer.intent is not Intent.RISK_COHORT:
        return None
    intro: list[str] = []
    rows: list[tuple[str, str, str]] = []
    notes: list[str] = []
    for sentence in _sentences(answer.text):
        found = re.match(r"^Score (?P<s>\d+): (?P<n>\d+) patients(?:, event rate (?P<r>[\d.]+%))?", sentence)
        if found:
            rows.append((f"Score {found.group('s')}", found.group("n"), found.group("r") or "no rate"))
        elif not rows:
            intro.append(sentence)
        else:
            notes.append(sentence)
    if not rows:
        return None
    return (
        "".join(f'<p class="p360-prose">{html.escape(s)}.</p>' for s in intro)
        + _table_html(("Score", "Members", "Observed event rate"), rows)
        + "".join(f'<p class="p360-note">{html.escape(s)}.</p>' for s in notes)
    )


def _refusal(answer: Answer) -> str:
    sentences = [s for s in _sentences(answer.text) if s != "Refused"]
    sentences = [s[len("Refused. "):] if s.startswith("Refused. ") else s for s in sentences]
    if not sentences:
        return '<p class="p360-summary">This question was refused.</p>'
    lead, rest = sentences[0], sentences[1:]
    rest_html = (
        '<ul class="p360-timeline">' + "".join(f"<li>{html.escape(s)}.</li>" for s in rest) + "</ul>"
        if rest
        else ""
    )
    return (
        f'<p class="p360-summary">{html.escape(lead)}.</p>{rest_html}'
        '<p class="p360-note">No rows were cited, so nothing was answered.</p>'
    )


def answer_card(answer: Answer) -> None:
    kind = "cited" if answer.status is AnswerStatus.CITED else "refused"
    label = "Cited answer" if kind == "cited" else "Refused"
    if kind == "refused":
        st.markdown(
            f'<div class="p360-answer refused"><div class="p360-kicker">{label}</div>{_refusal(answer)}</div>',
            unsafe_allow_html=True,
        )
        return
    for build in (_clinical_list, _row_table, _evidence_check, _risk_answer):
        body = build(answer)
        if body is not None:
            st.markdown(
                f'<div class="p360-answer cited"><div class="p360-kicker">{label}</div>{body}</div>',
                unsafe_allow_html=True,
            )
            return
    narrative = _member_narrative(answer)
    if narrative is not None:
        st.markdown(
            f'<div class="p360-answer {kind}"><div class="p360-kicker">{label}</div>{narrative}</div>',
            unsafe_allow_html=True,
        )
        return
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
