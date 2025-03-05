# api/kis_websocket.py
import json
import asyncio
import websockets
import logging
import requests
from datetime import datetime, timedelta, time as dtime
from requests.exceptions import RequestException
from websockets.exceptions import ConnectionClosed
from config.config import R_APP_KEY, R_APP_SECRET, M_APP_KEY, M_APP_SECRET
from config.condition import SELLING_POINT_UPPER, RISK_MGMT_UPPER
from utils.slack_logger import SlackLogger
from database.db_manager import DatabaseManager

class KISWebSocket:
    def __init__(self, callback=None, is_mock=True):
        # 내부 의존성 초기화: DB, 슬랙 로거 등
        self.db_manager = DatabaseManager()
        self.slack_logger = SlackLogger()
        self.callback = callback  # 매도 주문 콜백 함수
        self.is_mock = is_mock

        # 웹소켓 관련 속성
        self.websocket = None
        self.is_connected = False
        self.subscribed_tickers = set()
        self.ticker_queues = {}      # 종목별 메시지 큐
        self.active_tasks = {}       # 종목별 모니터링 태스크
        self.background_tasks = set()  # 전체 백그라운드 태스크 집합

        # 승인 및 연결 헤더 관련
        self.approval_key = None
        self.connect_headers = {
            "approval_key": self.approval_key,
            "custtype": "P",
            "tr_type": "1",
            "content-type": "utf-8"
        }

        # 종목별 락 관리 (매도 처리 시 동시 접근 방지)
        self.locks = {}
        self.LOCK_TIMEOUT = 10  # 초

        # 메시지 수신용 큐
        self.message_queue = asyncio.Queue()

    async def _get_approval(self, app_key, app_secret, approval_type, max_retries=3, retry_delay=5):
        """웹소켓 인증키(approval key) 발급 및 캐싱 처리"""
        cached_approval, cached_expires_at = self.db_manager.get_approval(approval_type)
        if cached_approval and cached_expires_at > datetime.utcnow():
            logging.info("Using cached %s approval", approval_type)
            return cached_approval, cached_expires_at

        url = "https://openapi.koreainvestment.com:9443/oauth2/Approval"
        headers = {"content-type": "application/json; utf-8"}
        body = {
            "grant_type": "client_credentials",
            "appkey": app_key,
            "secretkey": app_secret
        }
        for attempt in range(max_retries):
            try:
                # blocking 호출을 비동기로 처리
                response = await asyncio.to_thread(requests.post, url, headers=headers, json=body, timeout=10)
                response.raise_for_status()
                approval_data = response.json()
                if "approval_key" in approval_data:
                    self.approval_key = approval_data["approval_key"]
                    expires_at = datetime.utcnow() + timedelta(seconds=86400)
                    self.db_manager.save_approval(approval_type, self.approval_key, expires_at)
                    logging.info("Obtained %s approval on attempt %d", approval_type, attempt+1)
                    return self.approval_key, expires_at
                else:
                    logging.warning("Unexpected approval response on attempt %d: %s", attempt+1, approval_data)
            except RequestException as e:
                logging.error("Error fetching %s approval on attempt %d: %s", approval_type, attempt+1, e)
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logging.error("Max retries reached for %s approval.", approval_type)
        return None, None

    async def _ensure_approval(self, is_mock):
        now = datetime.now()
        if is_mock:
            if not hasattr(self, 'mock_approval') or self.mock_approval is None or now >= self.mock_approval_expires_at:
                self.mock_approval, self.mock_approval_expires_at = await self._get_approval(M_APP_KEY, M_APP_SECRET, "mock")
            return self.mock_approval
        else:
            if not hasattr(self, 'real_approval') or self.real_approval is None or now >= self.real_approval_expires_at:
                self.real_approval, self.real_approval_expires_at = await self._get_approval(R_APP_KEY, R_APP_SECRET, "real")
            return self.real_approval

    async def connect_websocket(self):
        """웹소켓 연결을 수립합니다."""
        try:
            if self.websocket and not self.websocket.closed:
                logging.info("WebSocket already connected.")
                return
            self.approval_key = await self._ensure_approval(self.is_mock)
            url = 'ws://ops.koreainvestment.com:31000/tryitout/H0STASP0'
            self.connect_headers = {
                "approval_key": self.approval_key,
                "custtype": "P",
                "tr_type": "1",
                "content-type": "utf-8"
            }
            self.websocket = await websockets.connect(url, extra_headers=self.connect_headers)
            self.is_connected = True
            logging.info("WebSocket connected successfully.")
        except Exception as e:
            logging.error("WebSocket connection failed: %s", e)
            self.is_connected = False

    async def close(self):
        """웹소켓 연결 종료 및 자원 정리"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            self.subscribed_tickers.clear()
            logging.info("WebSocket connection closed.")

    async def subscribe_ticker(self, ticker):
        """종목 구독 요청"""
        if ticker in self.subscribed_tickers:
            logging.info("Ticker %s already subscribed.", ticker)
            return
        self.connect_headers['tr_type'] = "1"
        request_data = {
            "header": self.connect_headers,
            "body": {"input": {"tr_id": "H0STASP0", "tr_key": ticker}}
        }
        try:
            await self.websocket.send(json.dumps(request_data))
            self.subscribed_tickers.add(ticker)
            logging.info("Subscribed to ticker: %s", ticker)
        except Exception as e:
            logging.error("Failed to subscribe ticker %s: %s", ticker, e)

    async def unsubscribe_ticker(self, ticker):
        """종목 구독 해제 요청"""
        if ticker not in self.subscribed_tickers:
            logging.info("Ticker %s is not subscribed.", ticker)
            return
        self.connect_headers['tr_type'] = "2"
        request_data = {
            "header": self.connect_headers,
            "body": {"input": {"tr_id": "H0STASP0", "tr_key": ticker}}
        }
        try:
            await self.websocket.send(json.dumps(request_data))
            self.subscribed_tickers.remove(ticker)
            logging.info("Unsubscribed ticker: %s", ticker)
        except Exception as e:
            logging.error("Failed to unsubscribe ticker %s: %s", ticker, e)

    async def add_new_stock_to_monitoring(self, session_id, ticker, name, qty, price, start_date, target_date):
        """새 종목을 모니터링 대상으로 추가합니다."""
        await self.subscribe_ticker(ticker)
        if ticker not in self.ticker_queues:
            self.ticker_queues[ticker] = asyncio.Queue()
        task = asyncio.create_task(self._monitor_ticker(session_id, ticker, name, qty, price, target_date))
        task.add_done_callback(self.background_tasks.discard)
        self.background_tasks.add(task)
        self.active_tasks[ticker] = task
        logging.info("Added monitoring task for ticker: %s", ticker)

    async def _monitor_ticker(self, session_id, ticker, name, quantity, avr_price, target_date):
        """개별 종목에 대한 모니터링 코루틴"""
        if ticker not in self.ticker_queues:
            self.ticker_queues[ticker] = asyncio.Queue()
        self.slack_logger.send_log(
            level="INFO",
            message="Monitoring started",
            context={"ticker": ticker, "avg_price": avr_price, "target_date": str(target_date), "quantity": quantity}
        )
        while self.is_connected and ticker in self.subscribed_tickers:
            try:
                recvvalue = await asyncio.wait_for(self.ticker_queues[ticker].get(), timeout=5.0)
                sell_completed = await self.sell_condition(recvvalue, session_id, ticker, name, quantity, avr_price, target_date)
                if sell_completed:
                    await self.unsubscribe_ticker(ticker)
                    logging.info("Sell completed for ticker: %s", ticker)
                    return True
                self.ticker_queues[ticker].task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logging.info("Monitoring cancelled for ticker: %s", ticker)
                return False
            except Exception as e:
                logging.error("Monitoring error for ticker %s: %s", ticker, e)
                continue
        return False

    async def sell_condition(self, recvvalue, session_id, ticker, name, quantity, avr_price, target_date):
        """
        매도 조건을 평가하고 조건이 충족되면 매도 주문을 실행합니다.
        """
        if len(recvvalue) == 1 and "SUBSCRIBE SUCCESS" in recvvalue[0]:
            return False
        try:
            target_price = int(recvvalue[15])
        except Exception as e:
            logging.error("Error parsing target price for ticker %s: %s", ticker, e)
            return False

        if ticker not in self.locks:
            self.locks[ticker] = asyncio.Lock()

        now = datetime.now()
        today = now.date()
        current_time = now.time()
        sell_time = dtime(15, 10)
        sell_reason = None
        if today > target_date and current_time >= sell_time:
            sell_reason = {"reason": "Expired holding period", "target_date": str(target_date)}
        elif target_price > (avr_price * SELLING_POINT_UPPER):
            sell_reason = {"reason": "Profit target reached", "target_price": target_price, "condition": avr_price * SELLING_POINT_UPPER}
        elif target_price < (avr_price * RISK_MGMT_UPPER):
            sell_reason = {"reason": "Risk management trigger", "target_price": target_price, "condition": avr_price * RISK_MGMT_UPPER}

        try:
            async with asyncio.timeout(self.LOCK_TIMEOUT):
                async with self.locks[ticker]:
                    if sell_reason:
                        try:
                            # 매도 주문 콜백 (동기 함수라면 asyncio.to_thread() 사용 가능)
                            sell_completed = self.callback(session_id, ticker, quantity, target_price)
                            await self.unsubscribe_ticker(ticker)
                            if sell_completed:
                                self.slack_logger.send_log(
                                    level="WARNING",
                                    message="Sell condition met",
                                    context={"ticker": ticker, **sell_reason}
                                )
                                await self.stop_monitoring(ticker)
                                return True
                        except Exception as e:
                            try:
                                await self.subscribe_ticker(ticker)
                                self.slack_logger.send_log(
                                    level="ERROR",
                                    message=f"Sell failed; subscription restored: {e}",
                                    context={"ticker": ticker}
                                )
                            except Exception as sub_error:
                                self.slack_logger.send_log(
                                    level="CRITICAL",
                                    message="Subscription restoration failed",
                                    context={"ticker": ticker, "error": str(sub_error)}
                                )
                            raise e
        except asyncio.TimeoutError:
            self.slack_logger.send_log(
                level="WARNING",
                message="Lock acquisition timeout",
                context={"ticker": ticker}
            )
            return False
        finally:
            if ticker in self.locks and not self.locks[ticker].locked():
                del self.locks[ticker]
        return False

    async def _message_receiver(self):
        """웹소켓 메시지 수신을 전담하는 코루틴"""
        while True:
            try:
                if not self.is_connected:
                    try:
                        await self.connect_websocket()
                        for ticker in self.subscribed_tickers:
                            await self.subscribe_ticker(ticker)
                    except Exception as e:
                        logging.error("Reconnection failed: %s", e)
                        await asyncio.sleep(5)
                        continue
                data = await self.websocket.recv()
                if '"tr_id":"PINGPONG"' in data:
                    await self.websocket.pong(data)
                    continue
                if "SUBSCRIBE SUCCESS" in data:
                    data_dict = json.loads(data)
                    ticker = data_dict['header']['tr_key']
                    continue
                recvvalue = data.split('^')
                if len(recvvalue) > 1:
                    ticker = recvvalue[0].split('|')[-1]
                    if ticker in self.subscribed_tickers:
                        await self.ticker_queues[ticker].put(recvvalue)
            except ConnectionClosed:
                logging.error("WebSocket connection closed. Reconnecting...")
                self.is_connected = False
                self.websocket = None
                await asyncio.sleep(1)
                continue
            except Exception as e:
                logging.error("Receiver error: %s", e)
                self.is_connected = False
                self.websocket = None
                await asyncio.sleep(1)
                continue

    async def real_time_monitoring(self, sessions_info):
        """
        실시간 모니터링을 시작합니다.
        sessions_info: List of tuples (session_id, ticker, name, quantity, avr_price, start_date, target_date)
        """
        try:
            if not self.is_connected:
                await self.connect_websocket()
            self.background_tasks = set()
            for session in sessions_info:
                session_id, ticker, name, qty, price, start_date, target_date = session
                await self.add_new_stock_to_monitoring(session_id, ticker, name, qty, price, start_date, target_date)
            asyncio.create_task(self._message_receiver())
            while self.background_tasks:
                done, _ = await asyncio.wait(self.background_tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    try:
                        await task
                    except Exception as e:
                        logging.error("Task error: %s", e)
            results = await asyncio.gather(*self.background_tasks, return_exceptions=True)
            logging.info("Monitoring results: %s", results)
            return results
        except Exception as e:
            logging.error("Real-time monitoring error: %s", e)
