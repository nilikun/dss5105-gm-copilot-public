"""The common tool envelope, typed errors and the evidence store (TOOL_SPEC §2)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.clock import Clock
from app.db.database import dumps, loads, next_id


class ErrorCode(StrEnum):
    NOT_FOUND = "NOT_FOUND"
    AMBIGUOUS = "AMBIGUOUS"
    OUT_OF_COVERAGE = "OUT_OF_COVERAGE"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    PRECONDITION_FAILED = "PRECONDITION_FAILED"


class ToolError(BaseModel):
    code: ErrorCode
    message: str
    candidates: list[dict[str, Any]] = Field(default_factory=list)


class EvidenceRef(BaseModel):
    id: str
    source: str
    keys: list[str]
    description: str


class ToolResult(BaseModel):
    ok: bool
    data: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    definition: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
    error: ToolError | None = None
    as_of: str


class EvidenceStore:
    """Registers the rows behind every figure so 'why?' goes back to the data (Tracing). Persisted, so a number
    clicked in the UI minutes later still opens its rows."""

    def __init__(self, db: sqlite3.Connection, clock: Clock, turn_id: str | None = None):
        self.db, self.clock, self.turn_id = db, clock, turn_id
        self.issued: list[str] = []  # evidence created during this context (the verifier's whitelist)

    def register(self, source: str, keys: list[str], description: str, rows: list[dict[str, Any]]) -> EvidenceRef:
        eid = next_id(self.db, "evidence", "E")
        self.db.execute("INSERT INTO evidence (evidence_id, source, keys, description, rows, as_of, turn_id) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (eid, source, dumps(keys), description, dumps(rows),
                         self.clock.now().isoformat(timespec="minutes"), self.turn_id))
        self.db.commit()
        self.issued.append(eid)
        return EvidenceRef(id=eid, source=source, keys=keys, description=description)

    def get(self, eid: str) -> dict[str, Any] | None:
        row = self.db.execute("SELECT * FROM evidence WHERE evidence_id = ?", (eid,)).fetchone()
        if row is None:
            return None
        return {"evidence_id": row["evidence_id"], "source": row["source"], "keys": loads(row["keys"]),
                "description": row["description"], "rows": loads(row["rows"]), "as_of": row["as_of"],
                "turn_id": row["turn_id"]}


@dataclass
class ToolContext:
    db: sqlite3.Connection
    clock: Clock
    turn_id: str | None = None
    evidence: EvidenceStore = field(init=False)

    def __post_init__(self) -> None:
        self.evidence = EvidenceStore(self.db, self.clock, self.turn_id)

    def ok(self, data: dict[str, Any], evidence: list[EvidenceRef] | None = None,
           definition: dict[str, Any] | None = None, warnings: list[str] | None = None) -> ToolResult:
        return ToolResult(ok=True, data=data, evidence=evidence or [], definition=definition,
                          warnings=warnings or [], as_of=self.clock.now().isoformat(timespec="minutes"))

    def fail(self, code: ErrorCode, message: str, candidates: list[dict[str, Any]] | None = None,
             warnings: list[str] | None = None) -> ToolResult:
        return ToolResult(ok=False, error=ToolError(code=code, message=message, candidates=candidates or []),
                          warnings=warnings or [], as_of=self.clock.now().isoformat(timespec="minutes"))
