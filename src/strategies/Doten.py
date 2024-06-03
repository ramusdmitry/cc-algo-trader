from hyperopt import hp

from src.bot import Bot
from src.indicators import highest, lowest


class Doten(Bot):
    def __init__(self):
        Bot.__init__(self, ["2h"])

    def options(self):
        return {
            "length": hp.randint("length", 1, 30, 1),
        }

    def strategy(self, action, open, close, high, low, volume, news=None):
        if action == "2h":
            lot = self.exchange.get_lot()
            length = self.input("length", int, 9)
            up = highest(high, length)[-1]
            dn = lowest(low, length)[-1]
            self.exchange.plot("up", up, "b")
            self.exchange.plot("dn", dn, "r")
            self.exchange.entry("Long", True, round(lot / 20), stop=up)
            self.exchange.entry("Short", False, round(lot / 20), stop=dn)
