"""The chart shell has to render the sentences the answer module already returns."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_STREAMLIT = Path(__file__).resolve().parents[2] / "streamlit"
if str(_STREAMLIT) not in sys.path:
    sys.path.insert(0, str(_STREAMLIT))

import chrome  # noqa: E402
import member_chart  # noqa: E402

from app.answers import answer_allergy, answer_risk  # noqa: E402
from app.assemble import assemble_answer  # noqa: E402
from app.questions import ALLERGY_QUESTION  # noqa: E402
from app.tests.fixtures import (  # noqa: E402
    INSPECTED_RISK_ROWS,
    WORKED_ALLERGY,
    WORKED_ALLERGY_SECTIONS,
    WORKED_PATIENT,
    WORKED_PATIENT_ID,
)


class UiAgreementTests(unittest.TestCase):
    def test_chart_does_not_claim_an_empty_allergy_list_is_absence(self) -> None:
        self.assertEqual(
            member_chart._NO_ALLERGY_ROWS,
            "No allergy rows are recorded in this dataset",
        )
        source = Path(member_chart.__file__).read_text(encoding="utf-8")
        self.assertNotIn("No allergy recorded", source)
        self.assertNotIn("No allergy is recorded", source)

    def test_allergy_card_quotes_the_csv_code_and_guards_the_other(self) -> None:
        answer = assemble_answer(
            ALLERGY_QUESTION,
            selected_patient_id=WORKED_PATIENT_ID,
            allergy_rows=[WORKED_ALLERGY],
            section_rows=list(WORKED_ALLERGY_SECTIONS),
            evidence_rows=[WORKED_PATIENT],
        )
        rendered = chrome._evidence_check(answer)
        self.assertIsNotNone(rendered)
        assert rendered is not None
        self.assertIn("Quoted code 609328004", rendered)
        self.assertIn("419199007", rendered)
        self.assertIn("Not quoted", rendered)

    def test_empty_allergy_card_stays_inside_the_dataset(self) -> None:
        answer = assemble_answer(
            ALLERGY_QUESTION,
            selected_patient_id=WORKED_PATIENT_ID,
            allergy_rows=[],
            evidence_rows=[WORKED_PATIENT],
        )
        rendered = chrome._evidence_check(answer)
        self.assertIsNotNone(rendered)
        assert rendered is not None
        self.assertIn("No allergy rows are recorded in this dataset", rendered)
        self.assertIn("not a claim that the member has no known allergies", rendered)

    def test_multiple_allergy_rows_are_all_on_the_card(self) -> None:
        second = dict(WORKED_ALLERGY)
        second["CODE"] = "232347008"
        second["DESCRIPTION"] = "Dander allergy"
        second["START"] = "2010-01-01"
        answer = answer_allergy(
            [WORKED_ALLERGY, second],
            list(WORKED_ALLERGY_SECTIONS),
            [WORKED_PATIENT],
        )
        rendered = chrome._evidence_check(answer)
        self.assertIsNotNone(rendered)
        assert rendered is not None
        self.assertIn("609328004", rendered)
        self.assertIn("232347008", rendered)

    def test_risk_card_reads_the_current_observed_rate_sentence(self) -> None:
        answer = answer_risk(list(INSPECTED_RISK_ROWS))
        rendered = chrome._risk_answer(answer)
        self.assertIsNotNone(rendered)
        assert rendered is not None
        self.assertIn("Score 2", rendered)
        self.assertIn("14.29%", rendered)
        self.assertIn("not recorded", rendered)
        self.assertIn("Score 2 sits below score 1", rendered)
        self.assertIn("not a validated stratifier", rendered)


if __name__ == "__main__":
    unittest.main()
