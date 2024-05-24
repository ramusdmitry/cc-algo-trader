from src.bot import Bot
from src.indicators import Supertrend


class SupertrendStrat(Bot):

    leverage = 1

    def __init__(self):
        Bot.__init__(self, ["4h"])
        self.supertrend = None

    def ohlcv_len(self):
        return 99

    def entry_position_size(self, balance):
        position = balance * self.leverage / self.exchange.get_market_price()
        return round(position, self.asset_rounding)

    def pnl(self, close, avg_entry_price, position_size, commission):

        profit = 0

        if abs(position_size):
            if avg_entry_price > close:
                close_rate = (avg_entry_price - close) / close - commission
                profit = round(position_size * close_rate * -close, self.quote_rounding)
            else:
                close_rate = (close - avg_entry_price) / avg_entry_price - commission
                profit = round(
                    position_size * close_rate * avg_entry_price, self.quote_rounding
                )

        return profit

    def liquidation_price(self, position_size, avg_entry_price, balance):

        if position_size >= 0:
            liquidation_price = (
                (position_size * avg_entry_price * 1.012) - balance
            ) / position_size  # long
        else:
            liquidation_price = (
                (position_size * avg_entry_price * 0.988) - balance
            ) / position_size  # short

        return round(liquidation_price, self.quote_rounding)

    def strategy(self, action, open, close, high, low, volume):
        self.asset_rounding = self.exchange.asset_rounding
        self.quote_rounding = self.exchange.quote_rounding
        self.exchange.leverage = self.leverage
        balance = self.exchange.get_balance()

        # ******************** Entry Type, Trade Type, Exit Type and Trigger Input ************************* #
        # -------------------------------------------------------------------------------------------------- #
        trade_side = None  # True for long only, False for short only, None trading both
        # -------------------------------------------------------------------------------------------------- #
        # -------------------------------------------------------------------------------------------------- #
        # ------- Parameters ------------------------------------------------------------------------------- #
        length = 10
        multiplier = 5
        # //////////////////////////////   Supertrend      ////////////////////////////////////////////////////

        if self.supertrend is None:
            self.supertrend = Supertrend(high, low, close, length, multiplier)

        # /////////////////////////////  Update Supertrend  ///////////////////////////////////////////////////
        self.supertrend.update(high, low, close)

        trend = self.supertrend.trend
        dir = self.supertrend.dir

        # ///////////////////////////////     Signals      /////////////////////////////////////////////////////

        long = dir[-1] == 1
        short = dir[-1] == -1

        # //////////////////////////////     Execution     /////////////////////////////////////////////////////

        if long and trade_side is not False:
            self.exchange.entry("Long", True, abs(self.entry_position_size(balance)))

        if short and trade_side is not True:
            self.exchange.entry("Short", False, abs(self.entry_position_size(balance)))

        # /////////////////////////////      Plot Supertrned    /////////////////////////////////////////////////

        if dir[-1] == 1:
            self.exchange.plot("st_uptrend", trend[-1], "b")
        else:
            self.exchange.plot("st_downtrend", trend[-1], "r")
