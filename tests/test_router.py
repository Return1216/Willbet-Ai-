"""意图目录加载、合法路由和安全回退测试。"""

import json
from pathlib import Path
from types import SimpleNamespace

from app.catalog import load_catalog
from app.router import route_intent


class FakeClient:
    """把指定字典包成 SDK 响应结构，便于测试模型输出校验。"""
    def __init__(self, payload):
        self.payload = payload
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(self.payload)))])


def test_catalog_has_all_intents():
    """确认当前意图树仍包含完整的 127 个意图。"""
    catalog = load_catalog((Path(__file__).resolve().parents[1] / "catalog" / "intent-tree-v1.json"))
    assert len(catalog.intents) == 127
    assert catalog.by_id["wallet.withdrawal.status.01"].need_realtime_data is True


def test_route_accepts_catalog_intent():
    """目录内且置信度足够的 ID 应被接受。"""
    catalog = load_catalog((Path(__file__).resolve().parents[1] / "catalog" / "intent-tree-v1.json"))
    decision = route_intent(
        "提现到哪里了？",
        {"page": "wallet"},
        {"user_id": "demo"},
        catalog,
        FakeClient({"intent": "wallet.withdrawal.status.01", "confidence": 0.92}),
    )
    assert decision.id == "wallet.withdrawal.status.01"
    assert decision.need_realtime_data is True
    assert decision.clarification is None


def test_route_falls_back_for_unknown_or_low_confidence():
    """未知 ID 或低置信度必须回退到澄清意图。"""
    catalog = load_catalog((Path(__file__).resolve().parents[1] / "catalog" / "intent-tree-v1.json"))
    unknown = route_intent("随便问问", {}, {}, catalog, FakeClient({"intent": "made.up", "confidence": 0.99}))
    assert unknown.id == "global.fallback"
    assert unknown.need_realtime_data is False

    low = route_intent("不能提现", {}, {}, catalog, FakeClient({"intent": "wallet.withdrawal.status.01", "confidence": 0.50}))
    assert low.id == "global.fallback"
    assert low.clarification
    assert low.need_realtime_data is False


def test_route_uses_configured_confidence_threshold():
    """路由器应使用调用方传入的置信度阈值。"""
    catalog = load_catalog((Path(__file__).resolve().parents[1] / "catalog" / "intent-tree-v1.json"))
    decision = route_intent(
        "提现到哪里了？", {}, {}, catalog,
        FakeClient({"intent": "wallet.withdrawal.status.01", "confidence": 0.80}),
        threshold=0.85,
    )
    assert decision.id == "global.fallback"
