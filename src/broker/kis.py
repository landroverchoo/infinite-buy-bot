"""
한국투자증권 OpenAPI 연동
TODO: 구현 필요
"""
from .base import Broker


class KISBroker(Broker):
    """한국투자증권"""

    def connect(self) -> bool:
        """TODO"""
        print("KIS API connection not implemented yet")
        return False

    def disconnect(self):
        pass

    def get_balance(self) -> float:
        return 0.0

    def get_positions(self, ticker: str = None):
        return {}

    def place_buy_order(self, ticker: str, price: float, shares: float, order_type: str = "market"):
        return {"status": "error", "message": "Not implemented"}

    def place_sell_order(self, ticker: str, price: float, shares: float, order_type: str = "market"):
        return {"status": "error", "message": "Not implemented"}

    def get_order_history(self, start_date: str, end_date: str):
        return []

    def get_current_price(self, ticker: str) -> float:
        return 0.0
