# process/main_process.py
import time
import threading
import atexit
from datetime import datetime
from process.scheduler_manager import SchedulerManager
from process.monitoring_manager import MonitoringManager
from trading.trading_logic import TradingLogic  # sell_order callback 제공을 위해 사용

class MainProcess:
    def __init__(self):
        self.stop_event = threading.Event()
        self.threads = {}
        self.scheduler_manager = SchedulerManager()
        # TradingLogic 인스턴스를 생성하여 매도 주문 콜백을 전달합니다.
        trading_logic = TradingLogic()
        self.monitoring_manager = MonitoringManager(sell_order_callback=trading_logic.sell_order)
        atexit.register(self.cleanup)

    def cleanup(self):
        self.scheduler_manager.shutdown()

    def start_all(self):
        # 스케줄러 스레드 시작
        print("스케줄러 스레드 시작")
        scheduler_thread = threading.Thread(
            target=self.scheduler_manager.start,
            name="SchedulerManager",
            daemon=True
        )
        scheduler_thread.start()
        self.threads['scheduler'] = scheduler_thread

        print("모니터링 스레드 시작")
        # 모니터링 스레드 시작
        monitoring_thread = threading.Thread(
            target=self.monitoring_manager.start,
            name="MonitoringManager"
        )
        monitoring_thread.start()
        self.threads['monitoring'] = monitoring_thread

    def stop_all(self):
        self.stop_event.set()
        for name, thread in self.threads.items():
            thread.join()

# if __name__ == "__main__":
#     main_process = MainProcess()
#     main_process.start_all()
#     start_time = datetime.now().strftime('%y%m%d - %X')
#     print("애플리케이션 시작 -", start_time)
#     try:
#         # 메인 스레드 무한 루프 (필요한 경우)
#         while True:
#             time.sleep(1)
#     except (KeyboardInterrupt, SystemExit):
#         print("\n프로그램 종료 요청됨")
#         main_process.stop_all()
#     finally:
#         main_process.cleanup()
