from hyperopt import hp

from src.bot import Bot
from src.indicators import rci


class Rci(Bot):
    def __init__(self):
        Bot.__init__(self, ["5m"])

    def options(self):
        return {
            "rcv_short_len": hp.quniform("rcv_short_len", 1, 10, 1),
            "rcv_medium_len": hp.quniform("rcv_medium_len", 5, 15, 1),
            "rcv_long_len": hp.quniform("rcv_long_len", 10, 20, 1),
        }

    def strategy(self, action, open, close, high, low, volume):
        lot = self.exchange.get_lot()

        itv_s = self.input("rcv_short_len", int, 5)
        itv_m = self.input("rcv_medium_len", int, 9)
        itv_l = self.input("rcv_long_len", int, 15)

        rci_s = rci(close, itv_s)
        rci_m = rci(close, itv_m)
        rci_l = rci(close, itv_l)

        long = ((-80 > rci_s[-1] > rci_s[-2]) or (-82 > rci_m[-1] > rci_m[-2])) and (
            rci_l[-1] < -10 and rci_l[-2] > rci_l[-2]
        )
        short = (
            (80 < rci_s[-1] < rci_s[-2]) or (rci_m[-1] < -82 and rci_m[-1] < rci_m[-2])
        ) and (10 < rci_l[-1] < rci_l[-2])
        close_all = 80 < rci_m[-1] < rci_m[-2] or -80 > rci_m[-1] > rci_m[-2]

        if long:
            self.exchange.entry("Long", True, lot)
        elif short:
            self.exchange.entry("Short", False, lot)
        elif close_all:
            self.exchange.close_all()
