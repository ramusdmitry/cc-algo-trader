from hyperopt import hp

from src import logger
from src.bot import Bot
from src.indicators import crossover, crossunder, sma


class Sample(Bot):
    def __init__(self):
        Bot.__init__(self, ["15m"])
        self.isLongEntry = []
        self.isShortEntry = []

    def options(self):
        return {
            "fast_len": hp.quniform("fast_len", 1, 20, 1),
            "slow_len": hp.quniform("slow_len", 1, 30, 1),
        }

    def ohlcv_len(self):
        return 100

    def strategy(self, action, open, close, high, low, volume, news=None):

        lot = self.exchange.get_lot()

        def entry_callback(avg_price=close[-1]):
            long = True if self.exchange.get_position_size() > 0 else False
            logger.info(f"{'Long' if long else 'Short'} Entry Order Successful")

        if action == "1m":
            pass
        if action == "15m":
            fast_len = self.input("fast_len", int, 6)
            slow_len = self.input("slow_len", int, 18)

            sma1 = sma(close, fast_len)
            sma2 = sma(close, slow_len)

            long_entry_condition = crossover(sma1, sma2)
            short_entry_condition = crossunder(sma1, sma2)

            self.exchange.sltp(profit_long=1.25, profit_short=1.25, stop_long=1, stop_short=1.1)

            if long_entry_condition:
                self.exchange.entry("Long", True, lot, callback=entry_callback)

            if short_entry_condition:
                self.exchange.entry("Short", False, lot, callback=entry_callback)

            self.isLongEntry.append(long_entry_condition)
            self.isShortEntry.append(short_entry_condition)
