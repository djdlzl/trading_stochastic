import logging

class TokenRepository:
    def __init__(self, db_manager):
        self.db_manager = db_manager  # DBConnectionManager 인스턴스
        self.cursor = self.db_manager.get_cursor()
        self._create_table()

    def _create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tokens (
                token_type VARCHAR(50) PRIMARY KEY,
                access_token TEXT,
                expires_at DATETIME
            ) ENGINE=InnoDB
        ''')
        self.db_manager.commit()

    def save_token(self, token_type, access_token, expires_at):
        try:
            self.cursor.execute('''
                INSERT INTO tokens (token_type, access_token, expires_at)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    access_token = VALUES(access_token),
                    expires_at = VALUES(expires_at)
            ''', (token_type, access_token, expires_at))
            self.db_manager.commit()
        except Exception as e:
            logging.error("Error saving token: %s", e)
            raise

    def get_token(self, token_type):
        try:
            self.cursor.execute(
                'SELECT access_token, expires_at FROM tokens WHERE token_type = %s',
                (token_type,)
            )
            result = self.cursor.fetchone()
            if result:
                return result.get('access_token'), result.get('expires_at')
            return None, None
        except Exception as e:
            logging.error("Error retrieving token: %s", e)
            raise
