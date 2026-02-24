"""
증권사 공통 인터페이스
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class Broker(ABC):
    """증권사 추상 클래스"""

    def __init__(self, credentials: Dict):
        self.credentials = credentials
        self.is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """API 연결"""
        pass

    @abstractmethod
    def disconnect(self):
        """연결 해제"""
        pass

    @abstractmethod
    def get_balance(self) -> float:
        """계좌 잔고 조회"""
        pass

    @abstractmethod
    def get_positions(self, ticker: Optional[str] = None) -> Dict:
        """보유 종목 조회"""
        pass

    @abstractmethod
    def place_buy_order(self, ticker: str, price: float, shares: float, order_type: str = "market") -> Dict:
        """매수 주문
        - ticker: 종목코드
        - price: 주문 가격 (지정가의 경우)
        - shares: 주문 수량
        - order_type: "market" (시장가), "limit" (지정가), "loc" (LOC)
        """
        pass

    @abstractmethod
    def place_sell_order(self, ticker: str, price: float, shares: float, order_type: str = "market") -> Dict:
        """매도 주문"""
        pass

    @abstractmethod
    def get_order_history(self, start_date: str, end_date: str) -> List[Dict]:
        """주문 내역 조회"""
        pass

    @abstractmethod
    def get_current_price(self, ticker: str) -> float:
        """현재가 조회"""
        pass
