# Cryptocurrency Algo Trader

## Описание

В репозитории представлена система, предназначенная для автоматизированной алгоритмической торговли на бирже Bybit
Derivatives и Spot.

Цель этой системы - предложить пользователям миниатюрную, простую и масштабируемую платформу для тестирования своих
стратегий с помощью бэктестинга и бумажной торговли, а также для совершения сделок в реальных условиях.


## Возможности

- Поддерживает **MAINNET** и **TESTNET** на Bybit
- Возможна торговля как на **SPOT**, так и на **FUTURES** (DERIVATIVES) рынке
- Взаимодействие с биржей Bybit посредствам REST API и WebSockets запросов
- Поддерживает ордера:
    - MARKET
    - LIMIT
    - STOP-LOSS
    - TAKE-PROFIT
    - TRAILING-STOP
    - ICEBERG
- Использует библиотеку TA-lib для технического анализа
- Возможна реализация и имплементация кастомных стратегий, позволяющая трейдерам определять собственные торговые
  алгоритмы и индикаторы
- Имеет систему бэктестинга для тестирования стратегий на исторических рыночных данных

## Доступные стратегии

1. Channel Breakout
1. Supertrend strategy
1. Parabolic SAR
1. MACD

1. Cross SMA
1. RCI
1. Open Close Cross Strategy

- Sanity checks
    1. CandleTesterMulti
    1. CandleTester

## Требования

- Python: 3.11
- TA-lib
- Docker

## Запуск

### 1. Установка зависимостей

#### MacOS

```bash
$ brew install ta-lib
$ pip install -r requirements.txt
```

### 2. Настройка конфигураций

В директории ``src/`` находится файл конфигурации бота ``config.py`` и файл конфигурации биржи ``exchange_config.py``

[BYBIT: Как создать свой API ключ?](https://www.bybit.com/ru-RU/help-center/article/How-to-create-your-API-key)

``.env``
```txt
BYBIT_API_KEY=1
BYBIT_SECRET_KEY=1
BYBIT_DEMO_API_KEY=6w8fNO1JmLkcYfcWmi
BYBIT_DEMO_SECRET_KEY=3gktnvOQd76eiMavwp12RDFh9lLWoxQAUSWH
```

``src/config.py``
```python
config = {
    "bybit_keys": {
        "bybitaccount1": {
            "API_KEY": os.getenv("BYBIT_API_KEY"),
            "SECRET_KEY": os.getenv("BYBIT_SECRET_KEY"),
        }
    },
    "bybit_test_keys": {
        "bybittest1": {
            "API_KEY": os.getenv("BYBIT_DEMO_API_KEY"),
            "SECRET_KEY": os.getenv("BYBIT_DEMO_SECRET_KEY"),
        }
    },

    "profiles": {
        "bybit_test_SAR_ETHUSDT": {
            "--test": False, 
            "--stub": False, 
            "--demo": False, # TESTNET
            "--hyperopt": False,
            "--spot": False, # SPOT / FUTURES
            "--account": "bybittest1", # ACCOUNT
            "--exchange": "bybit", # EXHANGE
            "--pair": "ETHUSDT", # PAIR
            "--strategy": "SAR", # STRATEGY
            "--session": None 
        }
    }
}
```
``src/exchange_config.py``

```python
"bybit": {
    "qty_in_usdt": False, # выставлять ордер в USDT, а не в монете
    "minute_granularity": False, # минутная грануляция данных
    "timeframes_sorted": True, # сортировка временем
    "enable_trade_log": True, # логирование
    "order_update_log": True, # логирование
    "ohlcv_len": 100, # длина свечи
    "call_strat_on_start": False, # немедленный запуск стратегии

    # Backtest
    "balance": 1000, # стартовый баланс
    "leverage": 1, # плечо
    "update_data": True, # обновлять данные
    "check_candles_flag": True,
    "days": 1200, # за какой период данные
    "search_oldest": 10, # (дней) - поиск самых старых исторических данных, 0 чтобы выключить
    "warmup_tf": None # Используется для загрузки данных, где необходима минутная грануляция
}
```


### 3. Запуск бота 

- `--account`: использовать данные от определённого аккаунта (обязательный аргумент)
- `--exchange`: использовать конкретную биржу (обязательный аргумент)
- `--pair`: выбор пары для торговли (обязательный аргумент)
- `--strategy`: использовать стратегию SAR. По умолчанию: doten (необязательный аргумент)

#### Примеры запуска

- BYBIT MAINNET (BYBITACCOUNT1) 
- STRATEGY: SAR
- PAIR: SOLUSDT
```bash
$ python main.py --account bybitaccount1 --exchange bybit --pair SOLUSDT --strategy SAR
```

- BYBIT TESTNET (BYBITTEST1) 
- STRATEGY: OCC
- PAIR: BTCUSDT
```bash
$ python main.py --demo --account bybittest1 --exchange bybit --pair BTCUSDT --strategy OCC
```



## 3. Тестирование

- **Backtest**

    В этом режиме скрипт будет проводить бэктест указанной стратегии (Sample) на исторических данных для указанной торговой пары (BTCUSDT) на
    бирже Bybit:
    
    ```bash
    $ python main.py --test --account bybitaccount1 --exchange bybit --pair BTCUSDT --strategy Sample
    ```

- **Hyperopt**

    Поиск наилучших значений гиперпараметров для оптимизации
    эффективности торговой стратегии:
    ```bash
    $ python main.py --hyperopt --account binanceaccount1 --exchange binance --pair BTCUSDT --strategy Sample
    ```

- **Papertrading**

    В этом режиме скрипт будет имитировать сделки на бирже для указанного торгового счета и торговой пары
    с использованием указанной стратегии. Никаких реальных сделок совершаться не будет. 
    
    ```bash
    $ python main.py --stub --account bybitaccount1 --exchange bybit --pair BTCUSDT --strategy Sample
    ```
