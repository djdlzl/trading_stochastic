# trading/session_manager.py
import random
import time
import asyncio
from datetime import datetime, date
from database.db_manager import DatabaseManager
from utils.date_utils import DateUtils
from utils.slack_logger import SlackLogger
from api.kis_api import KISApi
from api.kis_websocket import KISWebSocket
from config.condition import DAYS_LATER, COUNT, SELL_WAIT

class SessionManager:
    def __init__(self, kis_api=None, slack_logger=None, date_utils=None):
        # 의존성 주입: 외부에서 인스턴스를 전달하거나 기본값 사용
        self.kis_api = kis_api if kis_api else KISApi(is_mock=True)
        self.slack_logger = slack_logger if slack_logger else SlackLogger()
        self.date_utils = date_utils if date_utils else DateUtils()

    def start_trading_session(self):
        """
        거래 세션을 시작하고, 각 세션별 주문을 실행한 후 결과 리스트를 반환합니다.
        """
        db = DatabaseManager()
        session_info = self.check_trading_session()
        fund = self.calculate_funds(session_info['slot'])
        
        # 신규 세션 생성(빈 슬롯 만큼)
        for _ in range(int(session_info['slot'])):
            self.add_new_session(fund)
        
        try:
            # 세션 시작 로그 전송
            self.slack_logger.send_log(
                level="INFO",
                message="트레이딩 세션 시작",
                context={
                    "세션수": session_info['session'],
                    "가용슬롯": session_info['slot']
                }
            )
            
            sessions = db.load_trading_session()
            db.close()
            if not sessions:
                print("진행 중인 거래 세션이 없습니다.")
                return []
            
            order_list = []
            for session in sessions:
                # 거래 횟수가 COUNT에 도달하면 건너뜁니다.
                if session.get("count") == COUNT:
                    print(f"{session.get('name')}은 {COUNT}번의 거래를 진행해 넘어갑니다.")
                    continue
                order_result = self.place_order_for_session(session)
                order_list.append(order_result)
            return order_list
        except Exception as e:
            db.close()
            print("Trading session 실행 중 에러:", e)
            return []

    def check_trading_session(self):
        """
        현재 진행 중인 거래 세션 수를 확인하고, 남은 슬롯 수를 계산합니다.
        """
        db = DatabaseManager()
        db.cursor.execute('SELECT COUNT(*) FROM trading_session')
        result = db.cursor.fetchone()
        session_count = result.get('COUNT(*)')
        slot_count = 3 - session_count
        db.close()
        return {'session': session_count, 'slot': slot_count}

    def add_new_session(self, fund):
        """
        새로운 거래 세션을 생성합니다.
        """
        db = DatabaseManager()
        exclude_nums = []  # 필요한 경우 기존 세션 ID를 수집
        random_id = self.generate_random_id(exclude=exclude_nums)
        today = datetime.now()
        count = 0
        spent_fund = 0
        quantity = 0
        avr_price = 0
        
        # 거래에 사용할 종목 할당 (allocate_stock는 TradingLogic과 공유하거나 별도 유틸로 분리 가능)
        stock = self.allocate_stock()
        if stock is None:
            db.close()
            return None
        
        db.save_trading_session(random_id, today, today, stock['ticker'], stock['name'], fund, spent_fund, quantity, avr_price, count)
        db.close()
        return random_id

    def place_order_for_session(self, session):
        """
        주어진 세션 정보를 바탕으로 매수 주문을 진행합니다.
        """
        time.sleep(0.9)  # API 호출 간 간격 조정
        db = DatabaseManager()
        result = self.kis_api.get_current_price(session.get('ticker'))
        price = int(result[0])
        
        # 매수금액 계산 (예시로 COUNT에 따른 비율 할당)
        ratio = round(100/COUNT) / 100
        fund_per_order = int(float(session.get('fund')) * ratio)
        if session.get('count') < COUNT - 1:
            quantity = fund_per_order / price
        else:
            remaining_fund = float(session.get('fund')) - session.get('spent_fund')
            quantity = remaining_fund / price
        quantity = int(quantity)
        
        # 주문 실행 및 미체결 주문 처리
        order_result = None
        if session.get('count') < COUNT:
            while True:
                order_result = self.kis_api.place_order(session.get('ticker'), quantity, order_type='buy')
                if order_result['msg1'] == '초당 거래건수를 초과하였습니다.':
                    print("초당 거래건수 초과, 재시도합니다.")
                    continue
                break
        
        # 첫 주문 실패시 세션 삭제
        if order_result['rt_cd'] == '1' and session.get('count') == 0:
            print("첫 주문 실패, 해당 세션을 삭제합니다:", session)
            db.delete_session_one_row(session.get('id'))
        db.close()
        return order_result

    def load_and_update_sessions(self, order_list):
        """
        거래 세션을 불러와 주문 결과에 따라 세션을 업데이트합니다.
        """
        db = DatabaseManager()
        try:
            sessions = db.load_trading_session()
            if not sessions:
                print("진행 중인 거래 세션이 없습니다.")
                return
            for index, session in enumerate(sessions):
                self.update_session(session, order_list[index])
            db.close()
        except Exception as e:
            print("세션 업데이트 중 에러 발생:", e)
            db.close()

    def update_session(self, session, order_result):
        """
        주문 결과에 따라 세션 정보를 업데이트합니다.
        """
        try:
            time.sleep(0.8)
            db = DatabaseManager()
            odno = order_result.get('output', {}).get('ODNO')
            if odno is not None:
                exec_result = self.kis_api.daily_order_execution_inquiry(odno)
                real_spent_fund = exec_result.get('output1')[0].get('tot_ccld_amt')
                real_quantity = exec_result.get('output1')[0].get('tot_ccld_qty')
                
                balance_result = self.kis_api.balance_inquiry()
                index_of_odno = next((i for i, d in enumerate(balance_result) if d.get('pdno') == session.get('ticker')), -1)
                avr_price = int(float(balance_result[index_of_odno].get("pchs_avg_pric")))
                print("업데이트된 매입 단가:", avr_price)
            else:
                print("주문 번호가 없으므로 세션 업데이트를 취소합니다. 사유:", order_result.get('msg1'))
                db.close()
                return

            current_date = datetime.now()
            if order_result.get('rt_cd') == "0":
                spent_fund = int(session.get('spent_fund')) + int(real_spent_fund)
                quantity = int(session.get('quantity')) + int(real_quantity)
                count = session.get('count') + 1
                db.save_trading_session(session.get('id'), session.get('start_date'), current_date, 
                                          session.get('ticker'), session.get('name'),
                                          session.get('fund'), spent_fund, quantity, avr_price, count)
                db.close()
                self.slack_logger.send_log(
                    level="INFO",
                    message="세션 업데이트",
                    context={
                        "세션ID": session.get('id'),
                        "종목명": session.get('name'),
                        "투자금액": session.get('fund'),
                        "사용금액": spent_fund,
                        "평균단가": avr_price,
                        "보유수량": quantity,
                        "거래횟수": count
                    }
                )
            else:
                print("주문 실패:", order_result.get('message'))
                db.close()
        except Exception as e:
            print("세션 업데이트 중 에러:", e)

    def monitor_for_selling(self, sessions_info):
        """
        비동기로 모니터링을 실행하여 매도 시점을 감지합니다.
        sessions_info는 (session_id, ticker, name, quantity, avr_price, start_date, target_date)의 리스트입니다.
        """
        async def _monitor():
            kis_ws = KISWebSocket(self.sell_order)
            complete = await kis_ws.real_time_monitoring(sessions_info)
            if complete:
                print("모니터링 정상 종료")
            else:
                print("모니터링 비정상 종료")
        return asyncio.run(_monitor())

    def sell_order(self, session_id, ticker, quantity, price=None):
        """
        매도 주문 실행 및 미체결 주문 처리 후 완료되면 해당 세션 삭제.
        """
        try:
            order_result = self.kis_api.place_order(ticker, quantity, order_type='sell', price=price)
            time.sleep(SELL_WAIT)
            unfilled_qty = self.order_complete_check(order_result)
            new_order_result = order_result
            while unfilled_qty > 0:
                cancel_result = self.kis_api.cancel_order(new_order_result.get('output').get('ODNO'))
                time.sleep(1)
                new_order_result = self.kis_api.place_order(ticker, unfilled_qty, order_type='sell')
                time.sleep(SELL_WAIT)
                unfilled_qty = self.order_complete_check(new_order_result)
            self.delete_finished_session(session_id)
            return True
        except Exception as e:
            print("매도 주문 중 에러 발생:", e)

    def order_complete_check(self, order_result):
        exec_result = self.kis_api.daily_order_execution_inquiry(order_result.get('output').get('ODNO'))
        unfilled_qty = int(exec_result.get('output1')[0].get('rmn_qty'))
        return unfilled_qty

    def delete_finished_session(self, session_id):
        db = DatabaseManager()
        db.delete_session_one_row(session_id)
        db.close()
        print(f"{session_id} 세션 삭제됨.")

    def get_session_info(self):
        db = DatabaseManager()
        sessions = db.load_trading_session()
        db.close()
        sessions_info = []
        for session in sessions:
            target_date = self.date_utils.get_target_date(
                date.fromisoformat(str(session.get('start_date')).split()[0]), DAYS_LATER
            )
            info = (
                session.get('id'),
                session.get('ticker'),
                session.get('name'),
                session.get('quantity'),
                session.get('avr_price'),
                session.get('start_date'),
                target_date
            )
            sessions_info.append(info)
        return sessions_info

    def generate_random_id(self, min_value=1000, max_value=9999, exclude=None):
        if exclude is None:
            exclude = []
        exclude_set = set(exclude)
        while True:
            random_id = random.randint(min_value, max_value)
            if random_id not in exclude_set:
                return random_id

    def calculate_funds(self, slot):
        data = self.kis_api.purchase_availability_inquiry()
        balance = float(data.get('output').get('nrcvb_buy_amt'))
        print("가용 현금:", balance)
        session_fund = 0
        with DatabaseManager() as db:
            sessions = db.load_trading_session()
            for session in sessions:
                session_fund += int(session.get('spent_fund'))
        try:
            if slot == 3:
                allocated = balance / 3
            elif slot == 2:
                allocated = (balance - session_fund) / 2
            elif slot == 1:
                allocated = (balance - session_fund)
            else:
                allocated = 0
            print("할당 자금:", allocated)
            return int(allocated)
        except Exception as e:
            print("자금 할당 에러:", e)
            return 0

    def allocate_stock(self):
        db = DatabaseManager()
        try:
            selected_stock = db.get_selected_stocks()
            if selected_stock:
                db.delete_selected_stock_by_no(selected_stock.get('no'))
                db.close()
                return selected_stock
            else:
                db.close()
                return None
        except Exception as e:
            print("종목 할당 에러:", e)
            return None