from src import logger
from src.bot import Bot


class CandleTester(Bot):
    def __init__(self):
        Bot.__init__(self, ["1m"])

    def options(self):
        return {}

    def strategy(self, action, open, close, high, low, volume, news=None):
        logger.info(f"open: {open[-1]}")
        logger.info(f"high: {high[-1]}")
        logger.info(f"low: {low[-1]}")
        logger.info(f"close: {close[-1]}")
        logger.info(f"volume: {volume[-1]}")
