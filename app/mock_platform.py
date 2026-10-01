"""本地实时数据 Mock 适配器。

返回稳定的演示数据，便于前端联调；接入真实平台时保持同一返回结构即可替换。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MockData:
    """实时数据、数据源标记和可选的前端操作入口。"""

    data: dict[str, Any]
    data_source: str = "mock_platform"
    actions: list[dict[str, Any]] | None = None


def _default_action(intent_id: str) -> dict[str, Any] | None:
    """按意图域返回演示导航路径，由前端决定如何处理。"""

    if intent_id.startswith("wallet."):
        return {"label": "打开钱包", "type": "navigate", "target": "/wallet"}
    if intent_id.startswith("sports."):
        return {"label": "打开体育", "type": "navigate", "target": "/sports"}
    if intent_id.startswith("casino."):
        return {"label": "打开娱乐城", "type": "navigate", "target": "/casino"}
    if intent_id.startswith("promotion."):
        return {"label": "查看活动", "type": "navigate", "target": "/promotions"}
    if intent_id.startswith("vip."):
        return {"label": "查看 VIP", "type": "navigate", "target": "/vip"}
    if intent_id.startswith("support."):
        return {"label": "联系客服", "type": "navigate", "target": "/support"}
    return None


def get_mock_data(intent_id: str, user_context: dict[str, Any], page_context: dict[str, Any]) -> MockData:
    """为目录中的任意意图生成可重复的 Mock 响应。"""

    # page_context 目前不参与演示数据计算；金额、状态和时间均为固定测试值。
    user_id = str(user_context.get("user_id", "demo-user-001"))
    data: dict[str, Any]
    if intent_id == "wallet.withdrawal.status.01":
        data = {"user_id": user_id, "status": "processing", "amount": 100, "currency": "USDT", "updated_at": "2026-10-01T10:00:00+08:00"}
    elif intent_id.startswith("wallet.turnover."):
        data = {"user_id": user_id, "required": 100, "completed": 55, "remaining": 45, "currency": "USDT"}
    elif intent_id.startswith("wallet.withdrawal."):
        data = {"user_id": user_id, "status": "blocked", "reason": "turnover_incomplete", "remaining_turnover": 45, "currency": "USDT"}
    elif intent_id.startswith("wallet.deposit."):
        data = {"user_id": user_id, "status": "available", "supported_currencies": ["USDT", "BTC"], "minimum_amount": 10, "currency": "USDT"}
    elif intent_id.startswith("wallet.history."):
        data = {"user_id": user_id, "records": [{"type": "deposit", "amount": 100, "currency": "USDT", "status": "completed"}]}
    elif intent_id.startswith("sports.my_bets.") or intent_id.startswith("sports.bet."):
        data = {"user_id": user_id, "bet_id": "demo-bet-001", "status": "settled", "stake": 10, "currency": "USDT"}
    elif intent_id.startswith("sports.betslip."):
        data = {"user_id": user_id, "min_stake": 1, "max_stake": 1000, "currency": "USDT"}
    elif intent_id.startswith("sports.search.") or intent_id.startswith("sports.event_info"):
        data = {"items": [{"id": "demo-event-001", "name": "Tottenham vs Aston Villa", "status": "upcoming"}]}
    elif intent_id.startswith("casino.history."):
        data = {"user_id": user_id, "records": [{"game": "Demo Baccarat", "stake": 10, "result": "win", "currency": "USDT"}]}
    elif intent_id.startswith("casino.search.") or intent_id.startswith("casino.provider."):
        data = {"items": [{"id": "demo-game-001", "name": "Demo Baccarat", "provider": "Demo Provider", "available": True}]}
    elif intent_id.startswith("promotion."):
        data = {"user_id": user_id, "promotion_id": "demo-promo-001", "status": "active", "progress": 55, "reward": 20, "currency": "USDT"}
    elif intent_id.startswith("vip."):
        data = {"user_id": user_id, "level": 2, "next_level": 3, "benefits": ["cashback", "priority_support"]}
    elif intent_id.startswith("global.") or intent_id.startswith("support."):
        data = {"available": True, "message": "Demo platform service is available."}
    else:
        data = {"user_id": user_id, "topic": intent_id, "available": True, "message": "This is deterministic demo data."}

    return MockData(data=data, actions=[_default_action(intent_id)] if _default_action(intent_id) else [])
