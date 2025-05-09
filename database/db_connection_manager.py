import mysql.connector
import logging
from config.config import DB_CONFIG
import os
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class DBConnectionManager:
    def __init__(self):
        # 환경 변수 디버깅
        logging.debug(f"DB_HOST: {os.getenv('DB_HOST')}")
        logging.debug(f"DB_USER: {os.getenv('DB_USER')}")
        logging.debug(f"DB_NAME: {os.getenv('DB_NAME')}")
        logging.debug(f"DB_PORT: {os.getenv('DB_PORT')}")
        
        # DB_CONFIG 전체 출력
        logging.debug(f"DB_CONFIG: {DB_CONFIG}")
        
        try:
            # 연결 시도 전 추가 로깅
            logging.info(f"데이터베이스 연결을 시도합니다... (호스트: {DB_CONFIG['host']}, 포트: {DB_CONFIG['port']})")
            
            # 연결 시도 및 타임아웃 설정
            self.conn = mysql.connector.connect(
                **DB_CONFIG,
                connection_timeout=10  # 10초 타임아웃 설정
            )
            
            # 연결 상태 확인
            if not self.conn.is_connected():
                raise mysql.connector.Error("데이터베이스 연결에 실패했습니다.")
            
            logging.info("데이터베이스 연결에 성공했습니다.")
        except mysql.connector.Error as e:
            logging.error(f"데이터베이스 연결 오류: {e}")
            logging.error(f"연결 시도 설정: {DB_CONFIG}")
            
            # 추가 진단 정보 로깅
            if 'Access denied' in str(e):
                logging.error("접근이 거부되었습니다. 사용자 권한을 확인해주세요.")
            elif 'Unknown database' in str(e):
                logging.error("데이터베이스가 존재하지 않습니다. 데이터베이스 이름을 확인해주세요.")
            
            raise
        except Exception as e:
            logging.error(f"예상치 못한 오류 발생: {e}")
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
