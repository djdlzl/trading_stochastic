# trading/trading_logic.py
import time
from config.condition import BUY_WAIT, SELL_WAIT, COUNT
from utils.slack_logger import SlackLogger
from api.kis_api import KISApi

class TradingLogic:
    def __init__(self, kis_api=None, slack_logger=None):
        self.kis_api = kis_api if kis_api else KISApi(is_mock=True)
        self.slack_logger = slack_logger if slack_logger else SlackLogger()

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
            from datetime import datetime
            today = datetime.now().date()
            current_day = today  # DateUtils의 is_business_day 로직을 적용 가능
            from database.db_manager import DatabaseManager
            db = DatabaseManager()
            if stocks_info:
                db.save_upper_limit_stocks(current_day.strftime('%Y-%m-%d'), stocks_info)
                print(current_day.strftime('%Y-%m-%d'), stocks_info)
            else:
                print("상한가 종목이 없습니다.")
            db.close()

    def select_stocks_to_buy(self):
        from database.db_manager import DatabaseManager
        db = DatabaseManager()
        selected_stocks = []
        tickers_with_prices = db.get_upper_limit_stocks_days_ago()
        print("이전 상한가 종목:", tickers_with_prices)
        for stock in tickers_with_prices:
            current_price, temp_stop_yn = self.kis_api.get_current_price(stock.get('ticker'))
            if int(current_price) > (int(stock.get('closing_price')) * 0.92) and temp_stop_yn == 'N':
                print(f"매수 후보 종목: {stock.get('ticker')}, {stock.get('name')}, 현재가: {current_price}")
                selected_stocks.append(stock)
        if selected_stocks:
            db.save_selected_stocks(selected_stocks)
        db.close()
        return selected_stocks

    def delete_old_stocks(self):
        from datetime import datetime, timedelta
        today = datetime.now().date()
        # DateUtils와 Holidays 처리가 필요함
        old_date = today - timedelta(days=60)
        old_date_str = old_date.strftime('%Y-%m-%d')
        from database.db_manager import DatabaseManager
        db = DatabaseManager()
        db.delete_old_stocks(old_date_str)
        db.close()

    def init_selected_stocks(self):
        from database.db_manager import DatabaseManager
        db = DatabaseManager()
        db.delete_selected_stocks()
        db.close()
