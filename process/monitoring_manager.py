# process/monitoring_manager.py
import asyncio
import logging
from trading.trading_logic import TradingLogic
from api.kis_websocket import KISWebSocket

class MonitoringManager:
    def __init__(self, sell_order_callback):
        self.trading_logic = TradingLogic()
        self.kis_websocket = KISWebSocket(callback=sell_order_callback)
        # trading_logic 내부에 웹소켓 인스턴스를 설정
        self.trading_logic.kis_websocket = self.kis_websocket

    async def run_monitoring(self):
        sessions_info = self.trading_logic.get_session_info_upper()
        await self.trading_logic.monitor_for_selling_upper(sessions_info)

    def start(self):
        # 새로운 이벤트 루프를 생성하여 모니터링 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.run_monitoring())
        except Exception as e:
            logging.error("Monitoring error: %s", e)
        finally:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()
