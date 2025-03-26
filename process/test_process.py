# process/main_process.py
import time
import threading
import atexit
from datetime import datetime
from process.scheduler_manager import SchedulerManager
from process.monitoring_manager import MonitoringManager
from trading.trading_logic import TradingLogic  # sell_order callback 제공을 위해 사용
from api.kis_api import KISApi
import json

class TestProcess:
    def __init__(self):
        self.stop_event = threading.Event()
        self.threads = {}
        self.scheduler_manager = SchedulerManager()
        # TradingLogic 인스턴스를 생성하여 매도 주문 콜백을 전달합니다.
        self.trading_logic = TradingLogic()
        self.kis_api = KISApi()
        self.monitoring_manager = MonitoringManager(sell_order_callback=self.trading_logic.sell_order)
        # atexit.register(self.cleanup)

    def test(self):
        # stock_rank = self.kis_api.get_volume_rank()
        # print(json.dumps(stock_rank, indent=2, ensure_ascii=False))
        updown_rank = self.kis_api.get_upAndDown_rank()
        print(json.dumps(updown_rank, indent=2, ensure_ascii=False))
