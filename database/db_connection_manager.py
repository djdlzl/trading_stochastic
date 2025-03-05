import mysql.connector
import logging
from config.config import DB_CONFIG
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
class DBConnectionManager:
    def __init__(self):
        try:
            self.conn = mysql.connector.connect(**DB_CONFIG)
        except mysql.connector.Error as e:
            logging.error(f"데이터베이스 연결 오류: {e}")
            raise

    def get_cursor(self):
        return self.conn.cursor(buffered=True, dictionary=True)

    def commit(self):
        if self.conn and self.conn.is_connected():
            self.conn.commit()

    def close(self):
        if self.conn and self.conn.is_connected():
            self.conn.commit()
            self.conn.close()
