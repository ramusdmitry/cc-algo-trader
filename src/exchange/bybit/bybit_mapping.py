bybit_order_type_mapping = {"Market": "MARKET", "Limit": "LIMIT"}

bybit_trigger_by_mapping = {
    "LastPrice": "CONTRACT_PRICE",
    "MarkPrice": "MARK_PRICE",
    "IndexPrice": "INDEX_PRICE",
    "UNKNOWN": "CONTRACT_PRICE",
    "CONTRACT_PRICE": "LastPrice",
    "MARK_PRICE": "MarkPrice",
    "INDEX_PRICE": "IndexPrice",
}

bybit_tif_mapping = {"GTC": "GTC", "IOC": "IOC", "FOK": "FOK", "PostOnly": "GTX"}

bybit_order_status_mapping = {
    "Created": "CREATED",
    "New": "NEW",
    "Rejected": "REJECTED",
    "PartiallyFilled": "PARTIALLY_FILLED",
    "Filled": "FILLED",
    "PendingCancel": "PENDING_CANCEL",
    "Cancelled": "CANCELED",
    "Untriggered": "UNTRIGGERED",
    "Triggered": "TRIGGERED",
    "Deactivated": "DEACTIVATED",
    "Active": "ACTIVE",
}
