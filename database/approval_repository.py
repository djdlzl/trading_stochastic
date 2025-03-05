import logging

class ApprovalRepository:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.cursor = self.db_manager.get_cursor()
        self._create_table()

    def _create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS approvals (
                approval_type VARCHAR(50) PRIMARY KEY,
                approval_key TEXT,
                expires_at DATETIME
            ) ENGINE=InnoDB
        ''')
        self.db_manager.commit()

    def save_approval(self, approval_type, approval_key, expires_at):
        try:
            self.cursor.execute('''
                INSERT INTO approvals (approval_type, approval_key, expires_at)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    approval_key = VALUES(approval_key),
                    expires_at = VALUES(expires_at)
            ''', (approval_type, approval_key, expires_at))
            self.db_manager.commit()
        except Exception as e:
            logging.error("Error saving approval: %s", e)
            raise

    def get_approval(self, approval_type):
        try:
            self.cursor.execute(
                'SELECT approval_key, expires_at FROM approvals WHERE approval_type = %s',
                (approval_type,)
            )
            result = self.cursor.fetchone()
            if result:
                return result.get('approval_key'), result.get('expires_at')
            return None, None
        except Exception as e:
            logging.error("Error retrieving approval: %s", e)
            raise
