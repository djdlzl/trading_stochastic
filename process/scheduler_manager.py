# process/scheduler_manager.py
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from config.condition import GET_ULS_HOUR, GET_ULS_MINUTE, GET_SELECT_HOUR, GET_SELECT_MINUTE, ORDER_HOUR_1, ORDER_MINUTE_1, ORDER_HOUR_2, ORDER_MINUTE_2
from trading.trading_logic import TradingLogic
from trading.session_manager import TradingSessionManager

class SchedulerManager:
    def __init__(self):
        executors = {'default': ThreadPoolExecutor(20)}
        self.scheduler = BackgroundScheduler(executors=executors, timezone='Asia/Seoul', daemon=False)

    def add_jobs(self):
        trading_logic = TradingLogic()
        trading_session_manager = TradingSessionManager()

        self.scheduler.add_job(
            trading_logic.fetch_and_save_previous_upper_limit_stocks,
            CronTrigger(hour=GET_ULS_HOUR, minute=GET_ULS_MINUTE),
            id='fetch_stocks',
            replace_existing=True
        )
        self.scheduler.add_job(
            trading_logic.select_stocks_to_buy,
            CronTrigger(hour=GET_SELECT_HOUR, minute=GET_SELECT_MINUTE),
            id='select_stocks',
            replace_existing=True
        )
        self.scheduler.add_job(
            trading_session_manager.start_trading_session,
            CronTrigger(hour=ORDER_HOUR_1, minute=ORDER_MINUTE_1),
            id='buy_task_1',
            replace_existing=True
        )
        self.scheduler.add_job(
            trading_session_manager.start_trading_session,
            CronTrigger(hour=ORDER_HOUR_2, minute=ORDER_MINUTE_2),
            id='buy_task_2',
            replace_existing=True
        )

    def start(self):
        self.add_jobs()
        self.scheduler.start()
        logging.info("Scheduler started with jobs: %s", self.scheduler.get_jobs())

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logging.info("Scheduler shutdown")
