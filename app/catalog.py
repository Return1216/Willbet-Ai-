from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Intent:
    id: str
    domain: str
    group: str
    name: str
    examples: tuple[str, ...]
    need_realtime_data: bool
    required_context: tuple[str, ...]
    action: dict[str, Any] | None


@dataclass(frozen=True)
class Catalog:
    intents: tuple[Intent, ...]
    by_id: dict[str, Intent]


def load_catalog(path: Path) -> Catalog:
    data = json.loads(path.read_text(encoding="utf-8"))
    intents = tuple(
        Intent(
            id=item["id"],
            domain=item["domain"],
            group=item["group"],
            name=item["name"],
            examples=tuple(item.get("examples", [])),
            need_realtime_data=bool(item.get("need_realtime_data", False)),
            required_context=tuple(item.get("required_context", [])),
            action=item.get("action"),
        )
        for item in data["intents"]
    )
    return Catalog(intents=intents, by_id={item.id: item for item in intents})
