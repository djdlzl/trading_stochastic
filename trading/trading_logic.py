# trading/trading_logic.py
import time
from config.condition import BUY_WAIT, SELL_WAIT, COUNT
from utils.slack_logger import SlackLogger
from api.kis_api import KISApi
from api.kis_market_data import KISMarketData
from api.kis_auth import KISAuth
from trading.trading_strategy import TradingStrategy
from database.db_manager import DatabaseManager
from datetime import datetime, timedelta


class TradingLogic:
    def __init__(self, kis_api=None, slack_logger=None):
        # 공통 의존성 초기화
        self.kis_api = kis_api if kis_api else KISApi(is_mock=True)
        self.slack_logger = slack_logger if slack_logger else SlackLogger()
        self.auth = KISAuth()
        # 종목별 TechnicalAnalysis와 TradingStrategy를 저장할 캐시
        self.technical_analyses = {}
        self.strategies = {}

    def get_technical_analysis(self, ticker: str):
        """ticker에 대한 TechnicalAnalysis 객체를 캐싱하거나 생성"""
        if ticker not in self.technical_analyses:
            market_data = KISMarketData(self.auth)
            self.technical_analyses[ticker] = TechnicalAnalysis(market_data, ticker)
        return self.technical_analyses[ticker]

    def get_strategy(self, ticker: str) -> TradingStrategy:
        """ticker에 대한 TradingStrategy 객체를 캐싱하거나 생성"""
        if ticker not in self.strategies:
            technical_analysis = self.get_technical_analysis(ticker)
            self.strategies[ticker] = TradingStrategy(technical_analysis)
        return self.strategies[ticker]

    def buy_order(self, ticker, quantity):
        try:
            self.slack_logger.send_log(
                level="INFO",
                message="매수 주문 시작",
                context={"종목코드": ticker, "주문수량": quantity, "주문타입": "매수"}
            )
            order_result = self.kis_api.place_order(ticker, quantity, order_type='buy')
            print("매수 주문 실행:", ticker, order_result)
            if order_result['rt_cd'] != '0':
                self.slack_logger.send_log(
                    level="ERROR",
                    message="매수 주문 실패",
                    context={"종목코드": ticker, "메시지": order_result.get('msg1')}
                )
                return order_result

            time.sleep(BUY_WAIT)
            unfilled_qty = self.order_complete_check(order_result)
            while unfilled_qty > 0:
                cancel_result = self.kis_api.cancel_order(order_result.get('output', {}).get('ODNO'))
                time.sleep(1)
                order_result = self.kis_api.place_order(ticker, unfilled_qty, order_type='buy')
                time.sleep(BUY_WAIT)
                unfilled_qty = self.order_complete_check(order_result)
            self.slack_logger.send_log(
                level="INFO",
                message="매수 주문 결과",
                context={"종목코드": ticker, "주문번호": order_result.get('output', {}).get('ODNO')}
            )
            return order_result
        except Exception as e:
            print("매수 주문 중 에러 발생:", e)
            return None

    def sell_order(self, ticker, quantity, price=None):
        try:
            order_result = self.kis_api.place_order(ticker, quantity, order_type='sell', price=price)
            print("매도 주문 실행:", ticker, quantity, price, order_result)
            time.sleep(SELL_WAIT)
            unfilled_qty = self.order_complete_check(order_result)
            while unfilled_qty > 0:
                cancel_result = self.kis_api.cancel_order(order_result.get('output', {}).get('ODNO'))
                time.sleep(1)
                order_result = self.kis_api.place_order(ticker, unfilled_qty, order_type='sell')
                time.sleep(SELL_WAIT)
                unfilled_qty = self.order_complete_check(order_result)
            return True
        except Exception as e:
            print("매도 주문 중 에러 발생:", e)
            return False

    def order_complete_check(self, order_result):
        exec_result = self.kis_api.daily_order_execution_inquiry(order_result.get('output', {}).get('ODNO'))
        unfilled_qty = int(exec_result.get('output1')[0].get('rmn_qty'))
        print("미체결 수량:", unfilled_qty)
        return unfilled_qty

    def fetch_and_save_previous_upper_limit_stocks(self):
        upper_limit_stocks = self.kis_api.get_upper_limit_stocks()
        if upper_limit_stocks:
            stocks_info = [(stock['mksc_shrn_iscd'], stock['hts_kor_isnm'], stock['stck_prpr'], stock['prdy_ctrt'])
                           for stock in upper_limit_stocks['output']]
            today = datetime.now().date()
            db = DatabaseManager()
            if stocks_info:
                db.save_upper_limit_stocks(today.strftime('%Y-%m-%d'), stocks_info)
                print(today.strftime('%Y-%m-%d'), stocks_info)
            else:
                print("상한가 종목이 없습니다.")
            db.close()

    def select_stocks_to_buy(self):
        db = DatabaseManager()
        selected_stocks = []
        tickers_with_prices = db.get_upper_limit_stocks_days_ago()  # 메서드 정의 필요
        print("이전 상한가 종목:", tickers_with_prices)
        for stock in tickers_with_prices:
            current_price, temp_stop_yn = self.kis_api.get_current_price(stock.get('ticker'))
            if int(current_price) > (int(stock.get('closing_price')) * 0.92) and temp_stop_yn == 'N':
                print(f"매수 후보 종목: {stock.get('ticker')}, {stock.get('name')}, 현재가: {current_price}")
                selected_stocks.append(stock)
        if selected_stocks:
            db.save_selected_stocks(selected_stocks)  # 메서드 정의 필요
        db.close()
        return selected_stocks

    def delete_old_stocks(self):
        today = datetime.now().date()
        old_date = today - timedelta(days=60)
        old_date_str = old_date.strftime('%Y-%m-%d')
        db = DatabaseManager()
        db.delete_old_stocks(old_date_str)
        db.close()

    def init_selected_stocks(self):
        db = DatabaseManager()
        db.delete_selected_stocks()
        db.close()

    def run_strategy(self, ticker: str):
        """전략 실행"""
        # 종목별 TechnicalAnalysis와 TradingStrategy 가져오기
        strategy = self.get_strategy(ticker)

        # 전일 Stochastic K 값 계산 (High, Low, Close 사용)
        prev_data = self.get_technical_analysis(ticker).data.shift(1)
        prev_fast_k_up = prev_data.apply(
            lambda row: 100 * (row['종가'] - row['저가']) / (row['고가'] - row['저가']) if row['고가'] != row['저가'] else 0,
            axis=1
        ).iloc[-1] if not prev_data.empty else None
        prev_fast_k_down = prev_data.apply(
            lambda row: 100 * (row['종가'] - row['저가']) / (row['고가'] - row['저가']) if row['고가'] != row['저가'] else 0,
            axis=1
        ).iloc[-1] if not prev_data.empty else None

        # 매수 조건 체크
        if strategy.should_buy_uptrend(prev_fast_k_up):
            current_price = float(self.kis_api.get_current_price(ticker)[0])
            quantity = self.calculate_quantity(current_price)
            order_result = self.buy_order(ticker, quantity)
            if order_result and order_result['rt_cd'] == '0':
                strategy.set_entry(current_price)
                print(f"상승 추세 매수: {ticker} at {current_price}")

        elif strategy.should_buy_downtrend(prev_fast_k_down):
            current_price = float(self.kis_api.get_current_price(ticker)[0])
            quantity = self.calculate_quantity(current_price)
            order_result = self.buy_order(ticker, quantity)
            if order_result and order_result['rt_cd'] == '0':
                strategy.set_entry(current_price)
                print(f"하락 추세 매수: {ticker} at {current_price}")

        # 매도 조건 체크 (실시간 모니터링은 별도로 처리)
        if strategy.entry_price:
            current_price = float(self.kis_api.get_current_price(ticker)[0])
            if strategy.is_uptrend() and strategy.should_sell_uptrend(current_price):
                self.sell_order(ticker, quantity, current_price)
                print(f"상승 추세 매도: {ticker}")
                strategy.entry_price = None
            elif strategy.is_downtrend() and strategy.should_sell_downtrend(current_price):
                self.sell_order(ticker, quantity, current_price)
                print(f"하락 추세 매도: {ticker}")
                strategy.entry_price = None

    def calculate_quantity(self, price: float) -> int:
        """자금에 따른 수량 계산"""
        available_fund = float(self.kis_api.purchase_availability_inquiry()['output']['nrcvb_buy_amt'])
        return int(available_fund / price / 3)  # 3개 세션 가정