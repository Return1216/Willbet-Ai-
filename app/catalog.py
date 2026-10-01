"""意图目录加载器。

目录 JSON 是路由器的唯一意图白名单，避免模型返回目录之外的意图 ID。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Intent:
    """一个可被模型选择的意图及其路由元数据。"""

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
    """按顺序保存全部意图，并提供按 ID 的快速查询表。"""

    intents: tuple[Intent, ...]
    by_id: dict[str, Intent]


def load_catalog(path: Path) -> Catalog:
    """从 JSON 文件加载意图目录并建立 ID 索引。"""

    data = json.loads(path.read_text(encoding="utf-8"))
    # 只把路由阶段需要的字段映射成数据类，原始 JSON 仍可独立扩展。
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
