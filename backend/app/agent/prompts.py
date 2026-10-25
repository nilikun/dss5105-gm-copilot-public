"""Load prompts from backend/prompts/*.md. Prompts are data, not code: each file has a front-matter header with
name and version, and ${placeholders} filled at render time (string.Template, so JSON braces are safe)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from string import Template

from app.config import PROMPT_DIR


@dataclass(frozen=True)
class Prompt:
    name: str
    version: str
    body: str

    def render(self, **values: object) -> str:
        return Template(self.body).substitute({k: str(v) for k, v in values.items()})

    @property
    def tag(self) -> str:
        return f"{self.name}@v{self.version}"


@cache
def load(name: str) -> Prompt:
    text = (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body = text
    if text.startswith("---"):
        _, header, body = text.split("---", 2)
        for line in header.strip().splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return Prompt(name=meta.get("name", name), version=meta.get("version", "0"), body=body.strip())
