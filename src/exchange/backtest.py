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

from src import (
    allowed_range_minute_granularity,
    find_timeframe_string,
    load_data,
    logger,
    resample,
)
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

    def close_all(self, post_only=False, callback=None, chaser=False):

        if self.get_position_size() == 0:
            return
        Stub.close_all(self, post_only, callback, chaser=chaser)
        self.close_signals.append(self.index)

    def close_all_at_price(self, price, callback=None, chaser=False):

        if self.get_position_size() == 0:
            return
        Stub.close_all_at_price(self, price, callback, chaser=chaser)
        self.close_signals.append(self.index)

    def crawler_run(self):
        self.df_ohlcv = self.df_ohlcv.set_index(self.df_ohlcv.columns[0])
        self.df_ohlcv.index = pd.to_datetime(self.df_ohlcv.index, errors="coerce")

        warmup_duration = allowed_range_minute_granularity[self.warmup_tf][3] * self.ohlcv_len

        if conf["args"].from_date != "epoch":
            cut_off_time = pd.to_datetime(conf["args"].from_date, utc=True) - np.timedelta64(warmup_duration, "m")
            self.df_ohlcv = self.df_ohlcv.loc[(self.df_ohlcv.index >= cut_off_time)]
            logger.info(f"OHLCV Buffer Start: {cut_off_time} - Strategy Start: {conf['args'].from_date} (Inclusive)")

        if conf["args"].to_date != "now":
            cut_off_time = pd.to_datetime(conf["args"].to_date, utc=True)
            self.df_ohlcv = self.df_ohlcv.loc[(self.df_ohlcv.index < cut_off_time)]
            logger.info(f"Strategy End: {conf['args'].to_date} (Exclusive)")

        start = time.time()

        self.warmup_len = (
            (allowed_range_minute_granularity[self.warmup_tf][3] * self.ohlcv_len)
            if self.minute_granularity
            else self.ohlcv_len
        )

        if self.timeframe_data is None:
            self.timeframe_data = {}
            for t in self.bin_size:
                self.timeframe_data[t] = (
                    resample(self.df_ohlcv, t, minute_granularity=self.minute_granularity)
                    if self.minute_granularity
                    else self.df_ohlcv
                )
                self.timeframe_info[t] = {
                    "allowed_range": (
                        allowed_range_minute_granularity[t][0] if self.minute_granularity else self.bin_size[0]
                    ),
                    "ohlcv": self.timeframe_data[t][:-1],
                    "last_action_index": (
                        math.ceil(self.warmup_len / allowed_range_minute_granularity[t][3])
                        if self.minute_granularity
                        else self.warmup_len
                    ),
                }

        for i in range(self.warmup_len):
            self.balance_history.append((self.get_balance() - self.start_balance))
            self.draw_down_history.append(self.max_draw_down_session_perc)

        for i in range(len(self.df_ohlcv) - self.warmup_len):
            self.data = self.df_ohlcv.iloc[i: i + self.warmup_len + 1, :]
            index = self.data.iloc[-1].name
            new_data = self.data.iloc[-1:]

            action = "1m" if (self.minute_granularity or len(self.timeframe_info) > 1) else self.bin_size[0]

            timeframes_to_process = [
                (allowed_range_minute_granularity[t][3] if self.timeframes_sorted is not None else t)
                for t in self.timeframe_info
                if self.timeframe_info[t]["allowed_range"] == action
            ]

            if self.timeframes_sorted:
                timeframes_to_process.sort(reverse=True)
            if not self.timeframes_sorted:
                timeframes_to_process.sort(reverse=False)

            for t in timeframes_to_process:
                if self.timeframes_sorted is not None:
                    t = find_timeframe_string(t)

                last_action_index = self.timeframe_info[t]["last_action_index"]

                if self.timeframe_data[t].iloc[last_action_index].name != new_data.iloc[0].name:
                    continue

                tf_ohlcv_data = self.timeframe_data[t].iloc[last_action_index - self.ohlcv_len: last_action_index + 1]

                close = tf_ohlcv_data["close"].values
                open = tf_ohlcv_data["open"].values
                high = tf_ohlcv_data["high"].values
                low = tf_ohlcv_data["low"].values
                volume = tf_ohlcv_data["volume"].values

                if (t == "1m" and self.minute_granularity) or not self.minute_granularity:
                    if self.get_position_size() > 0 and low[-1] > self.get_trail_price():
                        self.set_trail_price(low[-1])
                    if self.get_position_size() < 0 and high[-1] < self.get_trail_price():
                        self.set_trail_price(high[-1])
                    self.market_price = close[-1]
                    self.OHLC = {"open": open, "high": high, "low": low, "close": close}

                    self.index = index
                    self.balance_history.append((self.get_balance() - self.start_balance))

                self.timestamp = tf_ohlcv_data.iloc[-1].name.isoformat().replace("T", " ")
                self.strategy(t, open, close, high, low, volume)
                self.timeframe_info[t]["last_action_index"] += 1

        self.close_all()
        logger.info(f"Back test time : {time.time() - start}")

    def security(self, bin_size, data=None):
        if data is None and bin_size not in self.bin_size:
            timeframe_list = [allowed_range_minute_granularity[t][3] for t in self.bin_size]
            timeframe_list.sort(reverse=True)
            t = find_timeframe_string(timeframe_list[-1])
            data = self.timeframe_data[t]

        self.resample_data[bin_size] = resample(data, bin_size)
        return self.resample_data[bin_size][: self.data.iloc[-1].name].iloc[-1 * self.ohlcv_len:, :]

    def check_candles(self, df):
        logger.info("-------")
        logger.info("Checking Candles:")
        logger.info("-------")
        logger.info(f"Start: {df.iloc[0][0]}")
        logger.info(f"End: {df.iloc[-1][0]}")
        logger.info("-------")

        diff = (dateutil.parser.isoparse(df.iloc[1][0]) - dateutil.parser.isoparse(df.iloc[0][0])).total_seconds()

        logger.info(f"Interval: {diff}s")
        logger.info("-------")

        count = 0
        rows = df.shape[0]
        for index in range(0, rows - 1):
            current_date = dateutil.parser.isoparse(df.iloc[index][0])
            next_date = dateutil.parser.isoparse(df.iloc[index + 1][0])

            diff2 = (next_date - current_date).total_seconds()
            if diff2 != diff:
                count += abs((diff2 - diff) / diff)
            elif diff2 <= 0:
                logger.info(f"Duplicate Candle: {current_date}")

        logger.info(f"Total Missing Candles = {count}")
        logger.info("-------")

    def save_csv(self, data, file):

        if not os.path.exists(os.path.dirname(file)):
            os.makedirs(os.path.dirname(file))

        data.to_csv(file, index_label="time")

    def load_ohlcv(self, bin_size):

        start_time = self.get_launch_date() + 1 * timedelta(days=1)
        end_time = datetime.now(timezone.utc)
        file = self.OHLC_FILENAME
        if len(bin_size) > 1:
            self.minute_granularity = True

        if self.minute_granularity and "1m" not in bin_size:
            bin_size.append("1m")

        self.bin_size = bin_size

        warmup = None

        for t in bin_size:
            if self.warmup_tf is None:
                warmup = allowed_range_minute_granularity[t][3]
                self.warmup_tf = t
            elif warmup < allowed_range_minute_granularity[t][3]:
                warmup = allowed_range_minute_granularity[t][3]
                self.warmup_tf = t
            else:
                continue

        if os.path.exists(file):
            self.df_ohlcv = load_data(file)
            self.df_ohlcv.set_index(self.df_ohlcv.columns[0], inplace=True)

            if self.update_data:
                self.df_ohlcv = self.df_ohlcv[:-1]  # exclude last candle
                data = self.download_data(
                    bin_size,
                    (
                        dateutil.parser.isoparse(self.df_ohlcv.iloc[-1].name)
                        if self.df_ohlcv.shape[0] > 0
                        else start_time
                    ),
                    end_time,
                )
                self.df_ohlcv = pd.concat([self.df_ohlcv, data])
                self.save_csv(self.df_ohlcv, file)

            self.df_ohlcv.reset_index(inplace=True)
            self.df_ohlcv = load_data(file)

        else:
            data = self.download_data(bin_size, start_time, end_time)
            self.save_csv(data, file)
            self.df_ohlcv = load_data(file)

        if self.check_candles_flag:
            self.check_candles(self.df_ohlcv)

    def show_result(self, plot=True):
        if conf["args"].html_report:
            DATA_FILENAME = self.OHLC_FILENAME
            shutil.copy(DATA_FILENAME, "html/data/data.csv")
            ORDERS_FILENAME = os.path.join(os.getcwd(), "./", conf["args"].order_log)
            shutil.copy(ORDERS_FILENAME, "html/data/orders.csv")

        result_info = {
            "TRADE COUNT": self.order_count,
            "BALANCE": self.get_balance(),
            "PROFIT RATE": self.get_balance() / self.start_balance * 100,
            "WIN RATE": 0 if self.order_count == 0 else self.win_count / (self.win_count + self.lose_count) * 100,
            "PROFIT FACTOR": self.win_profit if self.lose_loss == 0 else self.win_profit / self.lose_loss,
            "SHARPE RATIO": sharpe_ratio(self.balance_history, 0),
            "MAX DRAW DOWN TOTAL": f"{round(self.max_draw_down_session, 4)} or {round(self.max_draw_down_session_perc, 2)}%"
        }

        logger.info("============== Result ================")
        for key, value in result_info.items():
            logger.info(f"{key:20}: {value}")
        logger.info("======================================")

        if not plot:
            return

        import matplotlib.pyplot as plt

        plt_num = len([k for k, v in self.plot_data.items() if not v["overlay"]]) + 2
        i = 1

        plt.figure(figsize=(12, 8))
        plt.suptitle(self.pair + f" - {self.bin_size}", fontsize=12)

        plt.subplot(plt_num, 1, i)
        plt.plot(self.df_ohlcv.index, self.df_ohlcv["high"])
        plt.plot(self.df_ohlcv.index, self.df_ohlcv["low"])

        for k, v in self.plot_data.items():
            if v["overlay"]:
                color = v["color"]
                filtered_columns = [col for col in self.df_ohlcv if col.startswith(k)]

                if len(filtered_columns) == 1:
                    plt.plot(self.df_ohlcv.index, self.df_ohlcv[k], color, label=k)
                else:
                    for column in filtered_columns:
                        plt.plot(
                            self.df_ohlcv.index,
                            self.df_ohlcv[column],
                            f"#{random.randint(0, 0xFFFFFF):06x}",
                            label=column,
                        )
                plt.legend(fontsize=5)
        plt.ylabel("Price(USD)")
        ymin = min(self.df_ohlcv["low"]) - 0.05
        ymax = max(self.df_ohlcv["high"]) + 0.05
        plt.vlines(self.buy_signals, ymin, ymax, "blue", linestyles="dashed", linewidth=1)
        plt.vlines(self.sell_signals, ymin, ymax, "red", linestyles="dashed", linewidth=1)
        plt.vlines(self.close_signals, ymin, ymax, "green", linestyles="dashed", linewidth=1)

        i = i + 1

        for k, v in self.plot_data.items():
            if not v["overlay"]:
                plt.subplot(plt_num, 1, i)
                color = v["color"]

                filtered_columns = [col for col in self.df_ohlcv if col.startswith(k)]

                if len(filtered_columns) == 1:
                    plt.plot(self.df_ohlcv.index, self.df_ohlcv[k], color, label=k)
                else:
                    for column in filtered_columns:
                        plt.plot(
                            self.df_ohlcv.index,
                            self.df_ohlcv[column],
                            f"#{random.randint(0, 0xFFFFFF):06x}",
                            label=column,
                        )

                plt.ylabel(f"{k}")
                plt.legend(fontsize=5)
                i = i + 1

        plt.subplot(plt_num, 1, i)
        plt.plot(self.df_ohlcv.index, self.balance_history)
        plt.hlines(
            y=0,
            xmin=self.df_ohlcv.index[0],
            xmax=self.df_ohlcv.index[-1],
            colors="k",
            linestyles="dashed",
        )
        plt.ylabel("PL(USD)")
        plt.show()

    def plot(self, name, value, color, overlay=True):
        try:
            if isinstance(value, dict):
                for k, v in value.items():
                    self.df_ohlcv.at[self.index, name + "_" + k] = v

            elif isinstance(value, (int, float, np.number)):
                self.df_ohlcv.at[self.index, name] = value
            else:
                raise ValueError("Invalid value type. Expected dict, integer, or float.")
        except Exception as e:
            print(f"Error: {e}")

        if name not in self.plot_data:
            self.plot_data[name] = {"color": color, "overlay": overlay}
