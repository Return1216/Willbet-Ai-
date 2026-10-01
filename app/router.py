from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .catalog import Catalog, Intent


@dataclass(frozen=True)
class IntentDecision:
    id: str
    confidence: float
    need_realtime_data: bool
    required_context: list[str]
    action: dict[str, Any] | None
    clarification: str | None = None


def _catalog_prompt(catalog: Catalog) -> str:
    entries = [
        {
            "id": item.id,
            "name": item.name,
            "examples": list(item.examples),
            "need_realtime_data": item.need_realtime_data,
        }
        for item in catalog.intents
    ]
    return json.dumps(entries, ensure_ascii=False, separators=(",", ":"))


def _message_content(response: Any) -> str:
    content = response.choices[0].message.content
    if isinstance(content, list):
        return "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return str(content or "")


def _fallback(catalog: Catalog, confidence: float, clarification: str | None = None) -> IntentDecision:
    fallback = catalog.by_id.get("global.fallback")
    return IntentDecision(
        id=fallback.id if fallback else "global.fallback",
        confidence=confidence,
        need_realtime_data=False,
        required_context=list(fallback.required_context) if fallback else [],
        action=fallback.action if fallback else None,
        clarification=clarification,
    )


def route_intent(
    question: str,
    page_context: dict[str, Any],
    user_context: dict[str, Any],
    catalog: Catalog,
    llm_client: Any,
    model: str = "deepseek-chat",
    threshold: float = 0.75,
) -> IntentDecision:
    prompt = (
        "你是 WillBet AI 意图路由器。只能从候选列表中选择一个 intent。"
        "只返回 JSON，格式为 {\"intent\":\"ID\",\"confidence\":0.0}。"
        "不要回答用户问题。候选列表如下：" + _catalog_prompt(catalog)
    )
    response = llm_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": question,
                        "page_context": page_context,
                        "user_context": user_context,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
        stream=False,
    )
    try:
        output = json.loads(_message_content(response))
        intent_id = str(output.get("intent", ""))
        confidence = max(0.0, min(1.0, float(output.get("confidence", 0.0))))
    except (ValueError, TypeError, json.JSONDecodeError):
        return _fallback(catalog, 0.0, "我暂时无法确定你要查询的内容，请换一种说法。")

    if intent_id not in catalog.by_id:
        return _fallback(catalog, confidence)
    if confidence < threshold:
        return _fallback(catalog, confidence, "你是想了解规则、查询当前状态，还是打开某个功能？")

    intent: Intent = catalog.by_id[intent_id]
    return IntentDecision(
        id=intent.id,
        confidence=confidence,
        need_realtime_data=intent.need_realtime_data,
        required_context=list(intent.required_context),
        action=intent.action,
    )


