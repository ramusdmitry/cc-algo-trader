import os
import time
from datetime import timedelta, datetime

import pandas as pd

from src import allowed_range, delta, logger, sync_obj_with_config
from src.exchange.backtest import BackTest
from src.exchange.bybit.bybit_stub import BybitStub
from src.exchange_config import exchange_config
from src.timescaledb.client import TimescaleDBClient


class BybitBackTest(BackTest, BybitStub):
    update_data = True
    minute_granularity = False
    check_candles_flag = True
    days = 120
    search_oldest = 10
    enable_trade_log = True
    start_balance = 0
    warmup_tf = None

    def __init__(self, account, pair):
        """
        Конструктор для класса BybitBackTest.
        Args:
            account (str): Аккаунт для использования в бэктесте.
            pair (str): Торговая пара для бэктеста.
        """
        BybitStub.__init__(self, account, pair=pair, threading=False)
        BackTest.__init__(self)

        self.pair = pair
        self.db_client = TimescaleDBClient()
        self.db_client.connect()

        sync_obj_with_config(exchange_config["bybit"], BybitBackTest, self)

    def on_update(self, bin_size, strategy):
        """
        Регистрация функции стратегии.
        Args:
            bin_size (str): Временной интервал для данных OHLCV.
            strategy (function): Функция стратегии, выполняемая в процессе бэктеста.
        """
        self.bin_size = bin_size
        self.set_paths("bybit", pair=self.pair, bin_size=self.bin_size)
        self.load_ohlcv(bin_size)

        BybitStub.on_update(self, bin_size, strategy)
        BackTest.crawler_run(self)

    def fetch_backtest_data(self, bin_size, start_time, end_time):
        """
        Запрос данных для бэктеста из TimescaleDB.
        """
        conditions = {
            'measurement': 'backtest_data',
            'tags': f'pair:{self.pair},bin_size:{bin_size}',
            'fields': f'start_time:{start_time},end_time:{end_time}'
        }
        return self.db_client.read(self.db_client.metrics_table, conditions)

    def store_backtest_result(self, result):
        """
        Сохранение результатов бэктеста в TimescaleDB.
        """
        self.db_client.create(
            self.db_client.metrics_table,
            {
                "time": datetime.utcnow(),
                "measurement": "backtest_result",
                "tags": f'pair:{self.pair}',
                "fields": f'result:{result}'
            }
        )

    def __del__(self):
        self.db_client.close()

    def download_data(self, bin_size, start_time, end_time):
        """
        Загрузка данных OHLCV для указанного временного интервала.
        Args:
            bin_size (str): Временной интервал.
            start_time (datetime): Начальное время.
            end_time (datetime): Конечное время.
        Returns:
            pd.DataFrame: Данные OHLCV.
        """
        data = pd.DataFrame()
        left_time = None
        source = None
        is_last_fetch = False
        file = self.OHLC_FILENAME
        search_left = self.search_oldest
        last_search_ts = None

        if self.minute_granularity:
            bin_size = "1m"
        else:
            bin_size = bin_size[0]

        while True:
            try:
                if left_time is None:
                    left_time = start_time
                    right_time = left_time + delta(allowed_range[bin_size][0]) * 99
                else:
                    left_time = source.iloc[-1].name
                    right_time = left_time + delta(allowed_range[bin_size][0]) * 99

                if right_time > end_time:
                    right_time = end_time
                    is_last_fetch = True

            except IndexError:
                start_time = start_time + timedelta(days=self.search_oldest if self.search_oldest else 1)
                left_time = None
                logger.info(
                    f"Failed to fetch data, start time is too far in history.\n\
                    >>>  Searching, please wait. <<<\n\
                    Searching for oldest viable historical data, next start time attempt: {start_time}"
                )
                time.sleep(0.25)
                continue

            source = self.fetch_ohlcv(bin_size=bin_size, start_time=left_time, end_time=right_time)

            if search_left and not os.path.exists(file):
                logger.info("Searching for older historical data.\n>>>  Searching, please wait. <<<")
                start_time = start_time - timedelta(days=self.search_oldest)
                left_time = None
                if len(source) == 0 or (last_search_ts is not None and last_search_ts == source.iloc[-1].name):
                    search_left = False
                    continue
                last_search_ts = source.iloc[-1].name
                time.sleep(0.25)
                continue

            data = pd.concat([data, source])

            if is_last_fetch:
                return data

            time.sleep(0.25)
