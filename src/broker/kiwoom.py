"""
키움증권 Open API+ 연동
TODO: 구현 필요 (Windows 전용)
"""
from .base import Broker


class KiwoomBroker(Broker):
    """키움증권"""

    def connect(self) -> bool:
        """TODO"""
        print("Kiwoom API connection not implemented yet. Requires Windows.")
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
