from src import sync_obj_with_config
from src.exchange.bybit.bybit import Bybit
from src.exchange.stub import Stub
from src.exchange_config import exchange_config


class BybitStub(Stub, Bybit):
    def __init__(self, account, pair, threading=True):
        """
        Constructor for BybitStub class.
        Args:
            account (str): The account identifier for the Bybit futures.
            pair (str): The trading pair for the Binance futures.
            threading (bool, optional): Condition for setting the 'is_running' flag.
                Default is True to indicate the stub is running.
        """
        Bybit.__init__(self, account, pair, threading=threading)
        Stub.__init__(self)

        self.pair = pair
        self.balance_ath = self.balance
        self.position_size = 0
        self.is_running = threading
        sync_obj_with_config(exchange_config["bybit"], BybitStub, self)

    def on_update(self, bin_size, strategy):
        """
        The method called when the 'on_update' function is called on an instance of 'BybitStub'.
        Args:
            bin_size (list): The size of the bin for updating.
            strategy (function): The strategy function to be executed during the update.
        Returns:
            None
        """

        def __override_strategy(self, action, open, close, high, low, volume):
            strategy(action, open, close, high, low, volume)

        self.__override_strategy = Stub.override_strategy(__override_strategy).__get__(self, BybitStub)

        Bybit.on_update(self, bin_size, self.__override_strategy)
