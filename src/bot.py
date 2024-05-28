import json
import os


from src.config import config as conf
from src.exchange.bybit.bybit import Bybit
from src.exchange.bybit.bybit_backtest import BybitBackTest
from src.exchange.bybit.bybit_stub import BybitStub


class Session:
    def __init__(self):
        self.__session_type__ = "object"

    def load(self, dict):
        self.__dict__.update(dict)


class Bot:
    params = {}
    account = None
    exchange_arg = None
    bin_size = "1h"
    pair = "BTCUSDT"
    cancel_all_orders_at_stop = True
    periods = 20
    test_net = False
    back_test = False
    stub_test = False
    spot = False
    plot = True
    session = Session()
    session_file = None
    session_file_name = None

    def __init__(self, bin_size):
        self.bin_size = bin_size

    def __del__(self):
        self.stop()

    def get_session(self):
        return self.session

    def set_session(self, session):
        self.session.load(session)


    def ohlcv_len(self):
        return 100

    def input(self, title, type, defval):
        p = {} if self.params is None else self.params
        if title in p:
            return type(p[title])
        else:
            return defval

    def strategy(self, action, open, close, high, low, volume):
        pass

    def run(self):
        if self.stub_test:
            if self.exchange_arg == "bybit":
                self.exchange = BybitStub(account=self.account, pair=self.pair)
            else:
                return
        elif self.back_test:
            if self.exchange_arg == "bybit":
                self.exchange = BybitBackTest(account=self.account, pair=self.pair)
        else:
            if self.exchange_arg == "bybit":
                self.exchange = Bybit(account=self.account, pair=self.pair, demo=self.test_net, spot=self.spot)

        if conf["args"].check_candles is not None:
            self.exchange.check_candles_flag = conf["args"].check_candles

        if conf["args"].update_ohlcv is not None:
            self.exchange.update_data = conf["args"].update_ohlcv

        self.exchange.ohlcv_len = self.ohlcv_len()
        self.exchange.on_update(self.bin_size, self.strategy)

        self.exchange.show_result(plot=self.plot)

    def stop(self):
        if self.exchange is None:
            return


        if self.session_file is not None:
            self.session_file.truncate(0)
            self.session_file.seek(0)
            json.dump(self.session, self.session_file, default=vars, indent=True)
            self.session_file.close()

        self.exchange.stop()
        if self.cancel_all_orders_at_stop:
            self.exchange.cancel_all()

        os._exit(0)
