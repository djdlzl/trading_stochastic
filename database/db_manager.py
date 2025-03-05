# database/db_manager.py
from database.db_connection_manager import DBConnectionManager
from database.token_repository import TokenRepository
from database.approval_repository import ApprovalRepository
from database.stock_repository import StockRepository
from database.trading_session_repository import TradingSessionRepository

class DatabaseManager:
    def __init__(self):
        # 내부적으로 새 DB 연결 매니저와 리포지토리들을 생성합니다.
        self.db_connection = DBConnectionManager()
        self.token_repo = TokenRepository(self.db_connection)
        self.approval_repo = ApprovalRepository(self.db_connection)
        self.stock_repo = StockRepository(self.db_connection)
        self.session_repo = TradingSessionRepository(self.db_connection)

    # 기존에 trading 코드에서 사용한 메서드들을 동일한 이름과 시그니처로 구현합니다.
    
    def save_token(self, token_type, access_token, expires_at):
        self.token_repo.save_token(token_type, access_token, expires_at)

    def get_token(self, token_type):
        return self.token_repo.get_token(token_type)

    def save_upper_limit_stocks(self, date, stocks):
        self.stock_repo.save_upper_limit_stocks(date, stocks)

    def get_upper_limit_stocks(self, start_date, end_date):
        return self.stock_repo.get_upper_limit_stocks(start_date, end_date)

    def save_trading_session(self, session_id, start_date, current_date, ticker, name, fund, spent_fund, quantity, avr_price, count):
        self.session_repo.save_trading_session(session_id, start_date, current_date, ticker, name, fund, spent_fund, quantity, avr_price, count)

    def load_trading_session(self, session_id=None):
        return self.session_repo.load_trading_session(session_id)

    def delete_session_one_row(self, session_id):
        self.session_repo.delete_session_one_row(session_id)

    def delete_old_stocks(self, date):
        self.stock_repo.delete_old_stocks(date)

    def get_selected_stocks(self):
        return self.stock_repo.get_selected_stocks()

    def delete_selected_stocks(self):
        self.stock_repo.delete_selected_stocks()

    def delete_selected_stock_by_no(self, no):
        self.stock_repo.delete_selected_stock_by_no(no)

    def close(self):
        self.db_connection.close()
