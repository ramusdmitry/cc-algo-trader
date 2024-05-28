import os
from dotenv import load_dotenv

load_dotenv('.env', override=True)

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
    }
}
