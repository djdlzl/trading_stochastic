from datetime import datetime, time
from utils.date_utils import DateUtils

class TradingStrategy:
    def __init__(self):
        self.date_utils = DateUtils
        self.entry_price = None
        self.entry_date = None

    def is_uptrend(self):
        """상승 추세 여부 판단"""
        return self.market_data.get_macd(25, 40, 15) > 0

    def is_downtrend(self):
        """하락 추세 여부 판단"""
        return self.market_data.get_macd(25, 40, 15) < 0

    def _is_time_to_check(self):
        """오후 3시 10분인지 확인"""
        now = datetime.now()
        return now.time() >= time(15, 10) and now.time() < time(15, 11)

    def should_buy_uptrend(self, prev_fast_k: float = None):
        """상승 추세 매수 조건 확인"""
        if not self.is_uptrend() or not self._is_time_to_check():
            return False

        fast_k_df = self.market_data.get_stochastic_fast(6, 10)
        slow_k_12_5_5 = self.market_data.get_stochastic_slow(12, 5, 5)['K'].iloc[-1]
        slow_kd_20_2_14 = self.market_data.get_stochastic_slow(20, 2, 14)
        
        fast_k = fast_k_df['K'].iloc[-1]
        slow_d_20_2_14 = slow_kd_20_2_14['D'].iloc[-1]
        slow_k_20_2_14 = slow_kd_20_2_14['K'].iloc[-1]

        ma_5 = self.market_data.get_ma(5)
        ma_25 = self.market_data.get_ma(25)
        ma_120 = self.market_data.get_ma(120)

        return (
            fast_k > 20 and (prev_fast_k is None or prev_fast_k < 20) and  # 전일 K < 20, 당일 K > 20
            fast_k < 50 and
            slow_k_12_5_5 > 20 and
            ma_25 > ma_5 and
            ma_120 > ma_5 and
            (slow_d_20_2_14 > 40 or (slow_d_20_2_14 <= 40 and slow_k_20_2_14 > slow_d_20_2_14))
        )

    def should_sell_uptrend(self):
        """상승 추세 매도 조건 확인"""
        if self.entry_price is None:
            return False

        fast_k = self.market_data.get_stochastic_fast(14, 7)['K'].iloc[-1]
        current_price = float(self.market_data.kis_market_data.get_current_price(self.market_data.ticker)[0])
        loss_percent = (current_price / self.entry_price - 1) * 100

        return fast_k > 90 or loss_percent < -3

    def should_buy_downtrend(self, prev_fast_k: float = None):
        """하락 추세 매수 조건 확인"""
        if not self.is_downtrend() or not self._is_time_to_check():
            return False

        fast_k_df = self.market_data.get_stochastic_fast(14, 7)
        slow_k_25_2_3 = self.market_data.get_stochastic_slow(25, 2, 3)['K'].iloc[-1]
        slow_kd_20_2_14 = self.market_data.get_stochastic_slow(20, 2, 14)

        fast_k = fast_k_df['K'].iloc[-1]
        slow_d_20_2_14 = slow_kd_20_2_14['D'].iloc[-1]
        slow_k_20_2_14 = slow_kd_20_2_14['K'].iloc[-1]

        return (
            fast_k > 20 and (prev_fast_k is None or prev_fast_k < 20) and
            slow_k_25_2_3 > 20 and
            (slow_d_20_2_14 > 40 or (slow_d_20_2_14 <= 40 and slow_k_20_2_14 > slow_d_20_2_14))
        )

    def should_sell_downtrend(self):
        """하락 추세 매도 조건 확인"""
        if self.entry_price is None or self.entry_date is None:
            return False

        fast_k = self.market_data.get_stochastic_fast(6, 10)['K'].iloc[-1]
        current_price = float(self.market_data.kis_market_data.get_current_price(self.market_data.ticker)[0])
        loss_percent = (current_price / self.entry_price - 1) * 100
        
        from utils.date_utils import DateUtils
        days_held = len(DateUtils.get_business_days(self.entry_date, datetime.now().date()))
        
        return fast_k > 85 or loss_percent < -3 or (days_held >= 10 and fast_k <= 85)

    def set_entry(self, price: float):
        """진입 가격과 날짜 설정"""
        self.entry_price = price
        self.entry_date = datetime.now().date()

    def _is_time_to_check(self):
            """오후 3시 10분인지 확인"""
            now = datetime.now()
            return now.time() >= time(15, 10) and now.time() < time(15, 11)

    def should_buy_uptrend(self, prev_fast_k: float = None):
        if not self.is_uptrend() or not self._is_time_to_check():
            return False

        fast_k_df = self.market_data.get_stochastic_fast(6, 10)
        slow_k_12_5_5 = self.market_data.get_stochastic_slow(12, 5, 5)['K'].iloc[-1]
        slow_kd_20_2_14 = self.market_data.get_stochastic_slow(20, 2, 14)

        fast_k = fast_k_df['K'].iloc[-1]
        slow_d_20_2_14 = slow_kd_20_2_14['D'].iloc[-1]
        slow_k_20_2_14 = slow_kd_20_2_14['K'].iloc[-1]

        ma_5 = self.market_data.get_ma(5)
        ma_25 = self.market_data.get_ma(25)
        ma_120 = self.market_data.get_ma(120)

        return (
            fast_k > 20 and (prev_fast_k is None or prev_fast_k < 20) and
            fast_k < 50 and
            slow_k_12_5_5 > 20 and
            ma_25 > ma_5 and
            ma_120 > ma_5 and
            (slow_d_20_2_14 > 40 or (slow_d_20_2_14 <= 40 and slow_k_20_2_14 > slow_d_20_2_14))
        )

    def should_sell_uptrend(self, current_price: float):
        if self.entry_price is None:
            return False
        fast_k = self.market_data.get_stochastic_fast(14, 7)['K'].iloc[-1]
        loss_percent = (current_price / self.entry_price - 1) * 100
        return fast_k > 90 or loss_percent < -3

    def should_buy_downtrend(self, prev_fast_k: float = None):
        if not self.is_downtrend() or not self._is_time_to_check():
            return False

        fast_k_df = self.market_data.get_stochastic_fast(14, 7)
        slow_k_25_2_3 = self.market_data.get_stochastic_slow(25, 2, 3)['K'].iloc[-1]
        slow_kd_20_2_14 = self.market_data.get_stochastic_slow(20, 2, 14)

        fast_k = fast_k_df['K'].iloc[-1]
        slow_d_20_2_14 = slow_kd_20_2_14['D'].iloc[-1]
        slow_k_20_2_14 = slow_kd_20_2_14['K'].iloc[-1]

        return (
            fast_k > 20 and (prev_fast_k is None or prev_fast_k < 20) and
            slow_k_25_2_3 > 20 and
            (slow_d_20_2_14 > 40 or (slow_d_20_2_14 <= 40 and slow_k_20_2_14 > slow_d_20_2_14))
        )

    def should_sell_downtrend(self, current_price: float):
        if self.entry_price is None or self.entry_date is None:
            return False

        fast_k = self.market_data.get_stochastic_fast(6, 10)['K'].iloc[-1]
        loss_percent = (current_price / self.entry_price - 1) * 100
        days_held = len(DateUtils.get_business_days(self.entry_date, datetime.now().date()))
        return fast_k > 85 or loss_percent < -3 or (days_held >= 10 and fast_k <= 85)