"""Turn the reviewers' calibration workbooks into the label files eval/calibrate.py compares.

    uv run --project backend --with openpyxl python eval/import_labels.py --workbook <private>/reviewer.xlsx \
        --output eval/calibration/results-v1/labels-<name>.jsonl
    uv run --project backend python eval/import_labels.py --merge a.jsonl b.jsonl \
        --adjudication eval/calibration/adjudication-v1.json \
        --output eval/calibration/results-v1/labels-adjudicated.jsonl

Only the 'Human Labels' sheet is read, and candidate text is checked against the packet so a label cannot silently
belong to a changed answer. With --merge, the reviewers' agreed labels stand and a disagreement takes the recorded
adjudication; a disagreement with no adjudication stops the merge. Nothing is decided here.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "eval/calibration/reviewer-packet-v1/candidates.jsonl"


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _when(value) -> str:
    if isinstance(value, (int, float)):  # an Excel date serial
        value = datetime(1899, 12, 30) + timedelta(days=int(value))
    return (value if isinstance(value, datetime) else datetime.fromisoformat(str(value))).isoformat()


def from_workbook(path: Path) -> list[dict]:
    import openpyxl

    rows = list(openpyxl.load_workbook(path, data_only=True)["Human Labels"].iter_rows(values_only=True))
    head = [str(h).strip().lower().replace(" ", "_") for h in rows[0]]
    candidates = {e["id"]: e["candidate"]["text"] for e in _rows(PACKET)}
    labels: dict[str, dict] = {}
    for row in (dict(zip(head, r, strict=False)) for r in rows[1:]):
        if row["candidate_text"] != candidates[row["id"]]:
            raise ValueError(f"{row['id']}: candidate text differs from the packet")
        if type(row["pass"]) is not bool or not row["reason"]:
            raise ValueError(f"{row['id']} {row['criterion_id']}: unfilled label")
        entry = labels.setdefault(row["id"], {"id": row["id"], "reviewer": row["reviewer"],
                                              "reviewed_at": _when(row["reviewed_at"]), "decisions": []})
        entry["decisions"].append({"criterion_id": row["criterion_id"], "pass": row["pass"],
                                   "excerpt": row["excerpt"] or "", "reason": row["reason"]})
    return [labels[i] for i in sorted(labels)]


def merge(first: list[dict], second: list[dict], adjudication: dict) -> list[dict]:
    decided = {(d["id"], d["criterion_id"]): d for d in adjudication["decisions"]}
    others = {r["id"]: {d["criterion_id"]: d for d in r["decisions"]} for r in second}
    reviewer = " + ".join(sorted({first[0]["reviewer"], second[0]["reviewer"]})) + " (adjudicated)"
    merged = []
    for row in first:
        decisions = []
        for mine in row["decisions"]:
            theirs = others[row["id"]][mine["criterion_id"]]
            key = (row["id"], mine["criterion_id"])
            if mine["pass"] == theirs["pass"]:
                decisions.append(mine)
            elif key in decided:
                chosen = decided[key]
                decisions.append({"criterion_id": mine["criterion_id"], "pass": chosen["pass"], "excerpt": "",
                                  "reason": f"Adjudicated: {chosen['rule']}"})
            else:
                raise ValueError(f"{key}: reviewers disagree and no adjudication is recorded")
        merged.append({"id": row["id"], "reviewer": reviewer,
                       "reviewed_at": max(row["reviewed_at"], next(r["reviewed_at"] for r in second
                                                                   if r["id"] == row["id"])),
                       "decisions": decisions})
    return merged


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workbook", type=Path)
    ap.add_argument("--merge", type=Path, nargs=2)
    ap.add_argument("--adjudication", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    if a.workbook:
        rows = from_workbook(a.workbook)
    else:
        rows = merge(_rows(a.merge[0]), _rows(a.merge[1]), json.loads(a.adjudication.read_text(encoding="utf-8")))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    print(f"{len(rows)} candidates, {sum(len(r['decisions']) for r in rows)} decisions")


if __name__ == "__main__":
    main()
