# main.py
from process.main_process import MainProcess
from process.test_process import TestProcess
import datetime
import time

if __name__ == "__main__":
    test_process = TestProcess()
    test_process.test()
