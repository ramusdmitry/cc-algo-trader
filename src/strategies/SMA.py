from hyperopt import hp

from src import logger
from src.bot import Bot
from src.indicators import crossover, crossunder, sma


class SMA(Bot):
    def __init__(self):
        Bot.__init__(self, ["2h"])

    def options(self):
        return {
            "fast_len": hp.quniform("fast_len", 1, 30, 1),
            "slow_len": hp.quniform("slow_len", 1, 30, 1),
        }

    def strategy(self, action, open, close, high, low, volume, news=None):
        lot = self.exchange.get_lot()
        fast_len = self.input("fast_len", int, 9)
        slow_len = self.input("slow_len", int, 27)
        fast_sma = sma(close, fast_len)
        slow_sma = sma(close, slow_len)
        golden_cross = crossover(fast_sma, slow_sma)
        dead_cross = crossunder(fast_sma, slow_sma)

        def entry_callback(avg_price=close[-1]):
            long = True if self.exchange.get_position_size() > 0 else False
            logger.info(f"{'Long' if long else 'Short'} Entry Order Successful")

        if golden_cross:
            self.exchange.entry("Long", True, lot, round_decimals=3, callback=entry_callback)
        if dead_cross:
            self.exchange.entry("Short", False, lot, round_decimals=3, callback=entry_callback)
