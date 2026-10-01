from pathlib import Path

from app.catalog import load_catalog
from app.mock_platform import get_mock_data


CATALOG = load_catalog(Path(r"C:\Users\Lyy\Desktop\RAG_AGENT\catalog\intent-tree-v1.json"))


def test_every_catalog_intent_has_deterministic_mock_data():
    for intent_id in CATALOG.by_id:
        first = get_mock_data(intent_id, {"user_id": "demo"}, {"page": "wallet"})
        second = get_mock_data(intent_id, {"user_id": "demo"}, {"page": "wallet"})
        assert first.data_source == "mock_platform"
        assert first.data
        assert first == second


def test_withdrawal_and_turnover_mock_values_are_explicit():
    withdrawal = get_mock_data("wallet.withdrawal.status.01", {"user_id": "demo"}, {})
    turnover = get_mock_data("wallet.turnover.04", {"user_id": "demo"}, {})

    assert withdrawal.data["status"] == "processing"
    assert withdrawal.data["amount"] == 100
    assert turnover.data["remaining"] == 45
    assert turnover.data["currency"] == "USDT"
