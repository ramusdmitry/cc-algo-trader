import os

config = {
    "bybit_keys": {
        "bybitaccount1": {
            "API_KEY": os.environ["BYBIT_API_KEY"], 
            "SECRET_KEY": os.environ["BYBIT_SECRET_KEY"],
        }
    },
    "bybit_test_keys": {
        "bybittest1": {
           "API_KEY": os.environ["BYBIT_DEMO_API_KEY"], 
            "SECRET_KEY": os.environ["BYBIT_DEMO_SECRET_KEY"],
        }
    }
}