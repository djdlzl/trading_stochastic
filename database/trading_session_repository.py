import logging

class TradingSessionRepository:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.cursor = self.db_manager.get_cursor()
        self._create_table()

    def _create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_session (
                id INT PRIMARY KEY,
                start_date DATE,
                `current_date` DATE,
                ticker VARCHAR(20),
                name VARCHAR(100),
                fund INT,
                spent_fund INT,
                quantity INT,
                avr_price INT,
                count INT
            ) ENGINE=InnoDB
        ''')
        self.db_manager.commit()

    def save_trading_session(self, session_id, start_date, current_date, ticker, name, fund, spent_fund, quantity, avr_price, count):
        try:
            self.cursor.execute('''
                INSERT INTO trading_session 
                (id, start_date, current_date, ticker, name, fund, spent_fund, quantity, avr_price, count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    start_date = VALUES(start_date),
                    current_date = VALUES(current_date),
                    ticker = VALUES(ticker),
                    name = VALUES(name),
                    fund = VALUES(fund),
                    spent_fund = VALUES(spent_fund),
                    quantity = VALUES(quantity),
                    avr_price = VALUES(avr_price),
                    count = VALUES(count)
            ''', (session_id, start_date, current_date, ticker, name, fund, spent_fund, quantity, avr_price, count))
            self.db_manager.commit()
        except Exception as e:
            logging.error("Error saving trading session: %s", e)
            raise

    def load_trading_session(self, session_id=None):
        try:
            if session_id:
                self.cursor.execute('SELECT * FROM trading_session WHERE id = %s', (session_id,))
            else:
                self.cursor.execute('SELECT * FROM trading_session')
            return self.cursor.fetchall()
        except Exception as e:
            logging.error("Error loading trading session: %s", e)
            raise

    def delete_session_row(self, session_id):
        try:
            self.cursor.execute('DELETE FROM trading_session WHERE id = %s', (session_id,))
            self.db_manager.commit()
        except Exception as e:
            logging.error("Error deleting session row: %s", e)
            raise
