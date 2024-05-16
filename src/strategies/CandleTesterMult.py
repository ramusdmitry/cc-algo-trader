from src import logger
from src.bot import Bot


class CandleTesterMult(Bot):
    def __init__(self):
        Bot.__init__(self, ["5m", "15m", "4h"])

        self.ohlcv = {}

        for i in self.bin_size:
            self.ohlcv[i] = open(f"ohlcv_{i}.csv", "w")
            self.ohlcv[i].write("time,open,high,low,close,volume\n")  # header

    def options(self):
        return {}

    def strategy(self, action, open, close, high, low, volume):

        if action not in ["5m", "15m", "4h"]:
            return

        logger.info("---------------------------")
        logger.info(f"Action: {action}")
        logger.info("---------------------------")
        logger.info(f"time: {self.exchange.timestamp}")
        logger.info(f"open: {open[-1]}")
        logger.info(f"high: {high[-1]}")
        logger.info(f"low: {low[-1]}")
        logger.info(f"close: {close[-1]}")
        logger.info(f"volume: {volume[-1]}")
        logger.info("---------------------------")
        self.ohlcv[action].write(
            f"{self.exchange.timestamp},{open[-1]},{high[-1]},{low[-1]},{close[-1]},{volume[-1]}\n"
        )
