import json
import requests
import logging
from requests.exceptions import RequestException
from utils.string_utils import unicode_to_korean
from config.config import R_APP_KEY, R_APP_SECRET, M_APP_KEY, M_APP_SECRET, M_ACCOUNT_NUMBER
from config.condition import BUY_DAY_AGO
from datetime import datetime, timedelta
from database.db_manager import DatabaseManager
import time

class KISAuth:
    """한국투자증권 API와 상호작용하기 위한 클래스입니다."""

    def __init__(self):
        """KISAuth 클래스의 인스턴스를 초기화합니다."""
        self.headers = {"content-type": "application/json; charset=utf-8"}
        self.w_headers = {"content-type": "utf-8"}
        self.real_token = None
        self.mock_token = None
        self.real_token_expires_at = None
        self.mock_token_expires_at = None
        self.real_approval = None
        self.mock_approval = None
        self.real_approval_expires_at = None
        self.mock_approval_expires_at = None
        self.hashkey = None
        self.upper_limit_stocks = {}
        self.watchlist = set()

######################################################################################
#########################    인증 관련 메서드   #######################################
######################################################################################

    def _get_token(self, app_key, app_secret, token_type, max_retries=3, retry_delay=5):
        """
        지정된 토큰 유형에 대한 액세스 토큰을 가져옵니다.

        Args:
            app_key (str): 애플리케이션 키
            app_secret (str): 애플리케이션 시크릿
            token_type (str): 토큰 유형 ('real' 또는 'mock')
            max_retries (int): 최대 재시도 횟수
            retry_delay (int): 재시도 간 대기 시간(초)

        Returns:
            tuple: (액세스 토큰, 만료 시간) 또는 실패 시 (None, None)
        """
        db_manager = DatabaseManager()
        
        # Check if we have a valid cached token
        cached_token, cached_expires_at = db_manager.get_token(token_type)
        if cached_token and cached_expires_at > datetime.utcnow():
            logging.info("Using cached %s token", token_type)
            return cached_token, cached_expires_at

        url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": app_key,
            "appsecret": app_secret
        }

        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=body, timeout=10)
                response.raise_for_status()
                token_data = response.json()
                
                if "access_token" in token_data:
                    access_token = token_data["access_token"]
                    expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 86400))
                    
                    # Save the new token to the database
                    db_manager.save_token(token_type, access_token, expires_at)
                    db_manager.close()
                    
                    logging.info("Successfully obtained and cached %s token on attempt %d", token_type, attempt + 1)
                    return access_token, expires_at
                else:
                    logging.warning("Unexpected response format on attempt %d: %s", attempt + 1, token_data)
            except RequestException as e:
                logging.error("An error occurred while fetching the %s token on attempt %d: %s", token_type, attempt + 1, e)
                if attempt < max_retries - 1:
                    logging.info("Retrying in %d seconds...", retry_delay)
                    time.sleep(retry_delay)
                else:
                    logging.error("Max retries reached. Unable to obtain %s token.", token_type)
        db_manager.close()
        return None, None

    def _ensure_token(self, is_mock):
        """
        유효한 토큰이 있는지 확인하고, 필요한 경우 새 토큰을 가져옵니다.

        Args:
            is_mock (bool): 모의 거래 여부

        Returns:
            str: 유효한 액세스 토큰
        """
        now = datetime.now()
        if is_mock:
            if not self.mock_token or now >= self.mock_token_expires_at:
                self.mock_token, self.mock_token_expires_at = self._get_token(M_APP_KEY, M_APP_SECRET, "mock")
            return self.mock_token
        else:
            if not self.real_token or now >= self.real_token_expires_at:
                self.real_token, self.real_token_expires_at = self._get_token(R_APP_KEY, R_APP_SECRET, "real")
            return self.real_token

######################################################################################
###############################    헤더와 해쉬   ########################################
######################################################################################

    def _set_headers(self, is_mock=False, tr_id=None):
        """
        API 요청에 필요한 헤더를 설정합니다.

        Args:
            is_mock (bool): 모의 거래 여부
            tr_id (str, optional): 거래 ID
        """
        token = self._ensure_token(is_mock)
        self.headers["authorization"] = f"Bearer {token}"
        self.headers["appkey"] = M_APP_KEY if is_mock else R_APP_KEY
        self.headers["appsecret"] = M_APP_SECRET if is_mock else R_APP_SECRET
        if tr_id:
            self.headers["tr_id"] = tr_id
        self.headers["tr_cont"] = ""
        self.headers["custtype"] = "P"

    def _get_hashkey(self, body, is_mock=False):
        """
        주어진 요청 본문에 대한 해시 키를 생성합니다.

        Args:
            body (dict): 요청 본문

        Returns:
            str: 생성된 해시 키
        """
        if is_mock:
            url = "https://openapivts.koreainvestment.com:29443/uapi/hashkey"
            self._set_headers(is_mock=True)

        else:
            url = "https://openapi.koreainvestment.com:9443/uapi/hashkey"
            self._set_headers(is_mock=False)


        
        try:
            response = requests.post(url=url, headers=self.headers, data=json.dumps(body), timeout=10)
            response.raise_for_status()
            tmp = response.json()
            self.hashkey = tmp['HASH']
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while fetching the hash key: {e}")
