# main.py
from process.main_process import MainProcess
from process.test_process import TestProcess
import datetime
import time

if __name__ == "__main__":
    main_process = MainProcess()

    print("초기화 완료")
    main_process.start_all()
    start_time = datetime.datetime.now().strftime('%y%m%d - %X')
    print("애플리케이션 시작 -", start_time)
    try:
        # 메인 스레드 무한 루프 (필요한 경우)
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("\n프로그램 종료 요청됨")
        main_process.stop_all()
    finally:
        main_process.cleanup()
