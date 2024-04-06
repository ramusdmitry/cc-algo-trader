# coding: UTF-8

import math
import os
import random
import shutil
import time
from datetime import datetime, timedelta, timezone

import dateutil.parser
import numpy as np
import pandas as pd

from src import (allowed_range_minute_granularity, find_timeframe_string,
                 load_data, logger, resample)
from src.config import config as conf
from src.exchange.stub import Stub
from src.indicators import sharpe_ratio

OHLC_DIRNAME = os.path.join(os.path.dirname(__file__), "./ohlc/{}/{}/{}")
OHLC_FILENAME = os.path.join(os.path.dirname(__file__), "./ohlc/{}/{}/{}/data.csv")


class BackTest(Stub):
    update_data = True
    minute_granularity = False
    check_candles_flag = True
    days = 120
    search_oldest = 10
    enable_trade_log = True
    start_balance = 0
    warmup_tf = None

    def __init__(self):
        Stub.__init__(self)
        self.market_price = 0
        self.start_balance = self.get_balance()
        self.df_ohlcv = None
        self.index = None
        self.time = None
        self.order_count = 0
        self.buy_signals = []
        self.sell_signals = []
        self.close_signals = []
        self.balance_history = []
        self.draw_down_history = []
        self.plot_data = {}
        self.resample_data = {}

    def get_market_price(self):

        return self.market_price

    def now_time(self):

        return self.time

    def set_paths(self, exchange, pair=None, bin_size=None):

        bin_size = self.bin_size if not bin_size else bin_size

        pair = self.pair if not pair else pair

        self.OHLC_DIRNAME = OHLC_DIRNAME.format(exchange, pair, bin_size)
        self.OHLC_FILENAME = OHLC_FILENAME.format(exchange, pair, bin_size)

    def commit(
        self,
        id,
        long,
        qty,
        price,
        need_commission=False,
        callback=None,
        reduce_only=False,
    ):

        Stub.commit(self, id, long, qty, price, need_commission, callback, reduce_only)

        if long:
            self.buy_signals.append(self.index)
        else:
            self.sell_signals.append(self.index)
