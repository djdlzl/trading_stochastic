import logging
from datetime import datetime

class StockRepository:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.cursor = self.db_manager.get_cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS upper_limit_stocks (
                date DATE,
                ticker VARCHAR(20),
                name VARCHAR(100),
                closing_price DECIMAL(10,2),
                upper_rate DECIMAL(5,2),
                PRIMARY KEY (date, ticker)
            ) ENGINE=InnoDB
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS selected_stocks (
                no INT AUTO_INCREMENT PRIMARY KEY,
                date DATE,
                ticker VARCHAR(20),
                name VARCHAR(100),
                closing_price DECIMAL(10,2)
            ) ENGINE=InnoDB
        ''')
        self.db_manager.commit()

    def save_upper_limit_stocks(self, date, stocks):
        try:
            for ticker, name, closing_price, upper_rate in stocks:
                self.cursor.execute('''
                    INSERT INTO upper_limit_stocks (date, ticker, name, closing_price, upper_rate)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        closing_price = VALUES(closing_price),
                        upper_rate = VALUES(upper_rate)
                ''', (date, ticker, name, float(closing_price), float(upper_rate)))
            self.db_manager.commit()
        except Exception as e:
            logging.error("Error saving upper limit stocks: %s", e)
            raise

    def get_upper_limit_stocks(self, start_date, end_date):
        try:
            self.cursor.execute('''
                SELECT date, ticker, name, closing_price 
                FROM upper_limit_stocks 
                WHERE date BETWEEN %s AND %s
                ORDER BY date, name
            ''', (start_date, end_date))
            return self.cursor.fetchall()
        except Exception as e:
            logging.error("Error retrieving upper limit stocks: %s", e)
            raise

    # selected_stocks, 삭제, 정렬 관련 메서드 등도 여기에 포함
