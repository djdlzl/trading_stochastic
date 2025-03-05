# api/kis_api.py
from api.kis_auth import KISAuth
from api.kis_market_data import KISMarketData
from api.kis_order import KISOrder

class KISApi:
    def __init__(self, is_mock=False):
        # 내부 모듈 초기화: 인증, 시장 데이터, 주문
        self.auth = KISAuth()
        self.market_data = KISMarketData(auth=self.auth)
        self.order = KISOrder(auth=self.auth)

    # 편의 메서드 제공 (외부 인터페이스)
    def get_current_price(self, ticker):
        """
        지정 종목의 현재 주가와 거래 정지 여부를 반환합니다.
        """
        return self.market_data.get_current_price(ticker)

    def get_upper_limit_stocks(self):
        """
        상한가 종목 목록을 반환합니다.
        """
        return self.market_data.get_upper_limit_stocks()

    def get_upAndDown_rank(self):
        """
        상승/하락 순위 정보를 반환합니다.
        """
        return self.market_data.get_upAndDown_rank()

    def get_stock_volume(self, ticker, days=3):
        """
        지정 종목의 최근 n일간 거래량을 반환합니다.
        """
        return self.market_data.get_stock_volume(ticker, days)

    def compare_volumes(self, volumes):
        """
        3일간 거래량 비교 결과(백분율 차이)를 반환합니다.
        """
        return self.market_data.compare_volumes(volumes)

    def get_basic_stock_info(self, ticker):
        """
        종목 기본 정보를 반환합니다.
        """
        return self.market_data.get_basic_stock_info(ticker)

    def place_order(self, ticker, quantity, order_type, price=None):
        """
        매수/매도 주문을 실행합니다.
        """
        return self.order.place_order(ticker, quantity, order_type, price)

    def sell_order(self, ticker, quantity, price=None):
        """
        매도 주문을 실행합니다.
        """
        return self.order.sell_order(ticker, quantity, price)

    def cancel_order(self, order_num):
        """
        주문취소를 실행합니다.
        """
        return self.order.cancel_order(order_num)

    def revise_order(self, order_num):
        """
        주문 정정을 실행합니다.
        """
        return self.order.revise_order(order_num)

    def purchase_availability_inquiry(self, ticker=None):
        """
        주문 가능 조회를 실행합니다.
        """
        return self.order.purchase_availability_inquiry(ticker)

    def daily_order_execution_inquiry(self, order_num):
        """
        일별 주문 체결 조회를 실행합니다.
        """
        return self.order.daily_order_execution_inquiry(order_num)

    def balance_inquiry(self):
        """
        잔고 조회를 실행합니다.
        """
        return self.order.balance_inquiry()
