"""Step 3: comparison replies rendered from validated fields, checked by the independent answer contracts.

The model's draft below is deliberately incomplete. Source-backed references were recomputed from the CSVs with
the standard library (eval/tests); synthetic edges change a fresh in-memory database only.
"""

import json
import sys
from pathlib import Path

import pytest

from app.agent.runtime import Agent
from app.clock import SimClock
from app.db.database import connect
from app.llm.fake import ScriptedLLM
from app.tools import call
from app.tools.base import ErrorCode, ToolContext

EVAL = Path(__file__).resolve().parents[2] / "eval"
sys.path.insert(0, str(EVAL))
from answer_contracts import check_answer  # noqa: E402

CASES = {c["id"]: c for c in json.loads((EVAL / "fixtures/answer_contracts.json").read_text(encoding="utf-8"))["cases"]}
CLOCK = "2026-04-01"
DAY = "2026-03-25"


def set_window(db, value):
    db.execute("UPDATE production_log SET pieces_completed = ? WHERE stage = 'ASSEMBLY' AND date < ? "
               "AND strftime('%w', date) != '0'", (value, DAY))


def set_day(db, value):
    db.execute("UPDATE production_log SET pieces_completed = ? WHERE stage = 'ASSEMBLY' AND date = ?", (value, DAY))


SYNTHETIC = {
    "P07": lambda db: set_window(db, 0),
    "P08": lambda db: db.execute("DELETE FROM production_log WHERE stage = 'ASSEMBLY' AND date < ?", (DAY,)),
    "P09": lambda db: (set_window(db, 100), set_day(db, 120)),
    "P10": lambda db: (set_window(db, 100), set_day(db, 100)),
    "P11": lambda db: db.execute("DELETE FROM production_log WHERE stage = 'ASSEMBLY' AND date = ?", (DAY,)),
    "P12": lambda db: set_day(db, 0),
}


def ask(case_id, draft_kind="answer", db=None):
    case = CASES[case_id]
    ref = case["reference"]
    db = db or connect()
    SYNTHETIC.get(case_id, lambda _: None)(db)
    db.commit()
    args = {"stage": ref["stage"], "on_date": ref["start"]}
    if ref["statistic"] == "mean":
        args["through_date"] = ref["end"]
    llm = ScriptedLLM([[("compare_to_normal", args)],
                       [("respond", {"kind": draft_kind, "headline": "Output changed."})]])
    return Agent(db, SimClock.at(CLOCK), llm).run(case["question"]), ref


def text(reply):
    return " ".join(p for p in (reply.headline, reply.details) if p)


@pytest.mark.parametrize("case_id", ["D35", "P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08", "P09", "P10",
                                     "P11", "P12"])
@pytest.mark.parametrize("repeat", range(3))
def test_rendered_reply_meets_the_contract_despite_an_incomplete_draft(case_id, repeat):
    reply, ref = ask(case_id, "refuse" if case_id == "D35" else "answer")
    assert check_answer(ref, {"kind": reply.kind, "text": text(reply)}) == [], text(reply)
    assert reply.kind == ref["expected_kind"] and reply.verifier_rejections == 0


def test_cause_question_is_a_refusal_even_if_the_model_said_answer():
    reply, ref = ask("D35", "answer")
    assert reply.kind == "refuse" and check_answer(ref, {"kind": reply.kind, "text": text(reply)}) == []


def test_verdict_answers_is_it_normal():
    db = connect()
    llm = ScriptedLLM([[("compare_to_normal", {"stage": "ASSEMBLY", "on_date": "2026-03-31"})],
                       [("respond", {"kind": "answer", "headline": "No."})]])
    r = Agent(db, SimClock.at(CLOCK), llm).run("Was assembly's output yesterday normal?")
    assert "Judged not normal: interrupt tier, z = -6.26, 6 low working days in a row." in r.headline
    assert "455 pieces on 2026-03-31, 40.2% below baseline" in r.headline and "761.5 pieces/day" in r.details


# ----------------------------------------------------------------- the renderer knows which question it owns
@pytest.mark.parametrize("question,draft", [
    ("Which worker on assembly is slowest?", {"kind": "refuse", "headline": "The data has no worker names."}),
    ("Stop assembly for a day to fix this.", {"kind": "reject", "headline": "I cannot stop a production line."}),
])
def test_other_replies_keep_the_model_wording(question, draft):
    llm = ScriptedLLM([[("compare_to_normal", {"stage": "ASSEMBLY", "on_date": "2026-03-31"})], [("respond", draft)]])
    r = Agent(connect(), SimClock.at(CLOCK), llm).run(question)
    assert r.kind == draft["kind"] and r.headline == draft["headline"]


def test_several_stages_or_other_tools_stay_with_the_model():
    draft = {"kind": "answer", "headline": "Assembly is the one below normal."}
    llm = ScriptedLLM([[("compare_to_normal", {"stage": "ALL", "on_date": "2026-03-31"})], [("respond", draft)]])
    assert Agent(connect(), SimClock.at(CLOCK), llm).run("How were the stages?").headline == draft["headline"]
    draft = {"kind": "answer", "headline": "Assembly is low and some orders are late."}
    llm = ScriptedLLM([[("compare_to_normal", {"stage": "ASSEMBLY"}), ("find_orders", {"overdue": True})],
                       [("respond", draft)]])
    assert Agent(connect(), SimClock.at(CLOCK), llm).run("Is assembly low; what is late?").headline == draft["headline"]


def test_a_wrong_figure_in_the_draft_cannot_reach_the_rendered_reply():
    bad = {"kind": "answer", "headline": "Assembly made about 300 fewer pieces than normal."}
    llm = ScriptedLLM([[("compare_to_normal", {"stage": "ASSEMBLY", "on_date": "2026-03-31"})], [("respond", bad)]])
    r = Agent(connect(), SimClock.at(CLOCK), llm).run("Was assembly's output yesterday normal?")
    assert "300" not in text(r) and r.kind == "answer" and r.verifier_rejections == 0


def test_quoted_value_stays_with_the_model():
    draft = {"kind": "answer", "headline": "900 would be normal for knitting."}
    llm = ScriptedLLM([[("compare_to_normal", {"stage": "KNITTING", "value": 900})], [("respond", draft)]])
    assert Agent(connect(), SimClock.at(CLOCK), llm).run("is 900 from knitting normal?").headline == draft["headline"]


# ----------------------------------------------------------------- the tool itself
@pytest.fixture
def ctx():
    return ToolContext(connect(), SimClock.at(CLOCK), "t1")


def test_evidence_includes_the_observed_row_not_only_the_baseline(ctx):
    r, _ = call(ctx, "compare_to_normal", {"stage": "ASSEMBLY", "on_date": "2026-03-31"})
    rows = ctx.evidence.get(r.evidence[0].id)["rows"]
    assert len(rows) == 21 and rows[-1] == {"date": "2026-03-31", "stage": "ASSEMBLY", "pieces_completed": 455,
                                            "role": "observed"}
    assert sum(x["role"] == "baseline" for x in rows) == 20


def test_period_counts_only_working_days_and_a_gap_gives_no_mean(ctx):
    r, _ = call(ctx, "compare_to_normal", {"stage": "ASSEMBLY", "on_date": "2026-03-25", "through_date": "2026-03-31"})
    res = r.data["results"][0]
    assert res["observed_days"] == 6 and res["actual"] == 425.5 and res["pct_vs_baseline"] == -44.5
    ctx.db.execute("DELETE FROM production_log WHERE stage = 'ASSEMBLY' AND date = '2026-03-27'")
    r, _ = call(ctx, "compare_to_normal", {"stage": "ASSEMBLY", "on_date": "2026-03-25", "through_date": "2026-03-31"})
    res = r.data["results"][0]
    assert res["actual"] is None and res["pct_vs_baseline"] is None and "incomplete" in r.warnings[0]


@pytest.mark.parametrize("args", [{"stage": "ASSEMBLY", "through_date": "2026-03-31"},
                                  {"stage": "ASSEMBLY", "on_date": "2026-03-31", "through_date": "2026-03-25"},
                                  {"stage": "ASSEMBLY", "on_date": "2026-03-25", "through_date": "2026-09-01"}])
def test_bad_periods_are_rejected(ctx, args):
    r, _ = call(ctx, "compare_to_normal", args)
    assert not r.ok and r.error.code == ErrorCode.INVALID_ARGUMENT


def test_sunday_is_closed_not_abnormal(ctx):
    r, _ = call(ctx, "compare_to_normal", {"stage": "ASSEMBLY", "on_date": "2026-03-29"})
    assert r.ok and r.data["closed"] is True
