from src import logger
from src.config import config as conf


class Stub:
    qty_in_usdt = False
    minute_granularity = False
    enable_trade_log = True
    balance = 1000
    leverage = 1

    def __init__(self):
        self.balance_ath = self.balance
        self.position_size = 0
        self.position_avg_price = 0
        self.order_count = 0
        self.win_count = 0
        self.lose_count = 0
        self.win_profit = 0
        self.lose_loss = 0
        self.drawdown = 0
        self.max_draw_down = 0
        self.max_draw_down_session = 0
        self.max_draw_down_session_perc = 0
        self.open_orders = []
        self.isLongEntry = [False, False]
        self.isShortEntry = [False, False]

        self.order_log = open(conf["args"].order_log, "w")
        self.order_log.write(
            "time,type,id,price,quantity,av_price,position,pnl,balance,drawdown\n"
        )

    def get_lot(self, **kwargs):
        return float(self.get_balance() * self.get_leverage() / self.get_market_price())

    def get_balance(self, **kwargs):
        return self.balance

    def set_leverage(self, leverage, **kwargs):
        self.leverage = leverage

    def get_leverage(self, **kwargs):
        return self.leverage

    def get_position_size(self, **kwargs):
        return self.position_size

    def get_position_avg_price(self):
        return self.position_avg_price

    def get_pnl(self):
        entry_price = self.get_position_avg_price()
        pnl = (self.market_price - entry_price) * 100 / entry_price
        return pnl

    def cancel_all(self):
        self.open_orders = []

    def commit(
        self,
        id,
        long,
        qty,
        price,
        need_commission=False,
        reduce_only=False,
        callback=None,
    ):
        self.order_count += 1

        qty = (
            abs(self.get_position_size())
            if abs(qty) > abs(self.get_position_size()) and reduce_only
            else abs(qty)
        )
        order_qty = qty if long else -qty

        if self.get_position_size() * order_qty > 0:
            next_qty = self.get_position_size() + order_qty
        else:
            if abs(order_qty) > abs(self.get_position_size()):
                next_qty = self.get_position_size() + order_qty
            else:
                next_qty = 0

        commission = self.get_commission() if need_commission else 0.0

        if (self.get_position_size() > 0 >= order_qty) or (
            self.get_position_size() < 0 < order_qty
        ):
            closing_qty = (
                -order_qty
                if abs(order_qty) < abs(self.get_position_size())
                else self.get_position_size()
            )
            if self.get_position_size() >= 0:
                close_rate = (
                    (price - self.get_position_avg_price())
                    / self.get_position_avg_price()
                ) - commission
            else:
                close_rate = (
                    (self.get_position_avg_price() - price)
                    / self.get_position_avg_price()
                ) - commission

            profit = (
                abs(closing_qty)
                * close_rate
                * (1 if self.qty_in_usdt else self.get_position_avg_price())
            )

            if profit > 0:
                self.win_profit += profit  # * self.get_market_price()
                self.win_count += 1
            else:
                self.lose_loss += -1 * profit  # * self.get_market_price()
                self.lose_count += 1
                if close_rate * self.leverage < self.max_draw_down:
                    self.max_draw_down = close_rate * self.leverage

            self.balance += profit  # * self.get_market_price() / 100

            if self.balance_ath < self.balance:
                self.balance_ath = self.balance
            if self.balance_ath > self.balance:
                if self.max_draw_down_session == 0:
                    self.max_draw_down_session = self.balance_ath - self.balance
                    self.max_draw_down_session_perc = (
                        (self.balance_ath - self.balance) / self.balance_ath * 100
                    )
                else:
                    if (
                        self.max_draw_down_session_perc
                        < (self.balance_ath - self.balance) / self.balance_ath * 100
                    ):  # if self.max_draw_down_session < self.balance_ath - self.balance:
                        self.max_draw_down_session = self.balance_ath - self.balance
                        self.max_draw_down_session_perc = (
                            (self.balance_ath - self.balance) / self.balance_ath * 100
                        )

            self.drawdown = (self.balance_ath - self.balance) / self.balance_ath * 100

            self.order_log.write(
                f"{self.timestamp},{'BUY' if long else 'SELL'},{id if next_qty == 0 else 'Reversal'},"
                f"{price},{-self.position_size if abs(next_qty) else order_qty},{self.position_avg_price},"
                f"{0 if abs(next_qty) else self.position_size+order_qty},{profit:.2f},{self.get_balance():.2f},{self.drawdown:.2f}\n"
            )
            self.order_log.flush()

            self.position_size = self.get_position_size() + order_qty

            if self.enable_trade_log:
                logger.info("========= Close Position =============")
                logger.info(f"ID            : {id if next_qty == 0 else 'Reversal'}")
                logger.info(f"TIME          : {self.timestamp}")
                logger.info(f"TRADE COUNT   : {self.order_count}")
                logger.info(f"POSITION SIZE : {self.position_size}")
                logger.info(f"ENTRY PRICE   : {self.position_avg_price}")
                logger.info(f"EXIT PRICE    : {price}")
                logger.info(f"PROFIT        : {profit}")
                logger.info(f"BALANCE       : {self.get_balance()}")
                logger.info(
                    f"WIN RATE      : {0 if self.order_count == 0 else self.win_count/(self.win_count + self.lose_count)*100} %"
                )
                logger.info(
                    f"PROFIT FACTOR : {self.win_profit if self.lose_loss == 0 else self.win_profit/self.lose_loss}"
                )
                logger.info(f"MAX DRAW DOWN : {abs(self.max_draw_down) * 100:.2f}%")
                logger.info(
                    f"MAX DRAW DOWN SESSION : {round(self.max_draw_down_session, 4)} or {round(self.max_draw_down_session_perc, 2)}%"
                )
                logger.info("======================================")

            if next_qty == 0 and callback is not None:
                callback()

        if next_qty != 0:
            if self.enable_trade_log:
                logger.info("********* Create Position ************")
                logger.info(f"TIME          : {self.timestamp}")
                logger.info(f"PRICE         : {price}")
                logger.info(f"TRADE COUNT   : {self.order_count}")
                logger.info(f"ID            : {id}")
                logger.info(
                    f"POSITION SIZE : {order_qty if next_qty * self.position_size > 0 else next_qty}"
                )
                logger.info("**************************************")

            if long and 0 < self.position_size < next_qty:
                self.position_avg_price = (
                    self.position_avg_price * self.position_size + price * qty
                ) / next_qty
            elif not long and 0 > self.position_size > next_qty:
                self.position_avg_price = (
                    self.position_avg_price * self.position_size - price * qty
                ) / next_qty
            else:
                self.position_avg_price = price
            self.position_size = next_qty
            logger.info("//////// Current Position ////////////")
            logger.info(
                f"current position size: {next_qty} at avg. price: {self.position_avg_price}"
            )

            self.order_log.write(
                f"{self.timestamp},{'BUY' if long else 'SELL'},{id},{price},"
                f"{next_qty if abs(order_qty) > abs(next_qty) else order_qty},"
                f"{self.position_avg_price},{self.position_size},{'-'},"
                f"{self.get_balance():.2f},{self.drawdown:.2f}\n"
            )
            self.order_log.flush()

            self.set_trail_price(price)

            if callback is not None:
                callback()

    def eval_exit(self):
        if self.get_position_size() == 0:
            return

        price = self.get_market_price()

        if self.get_exit_order()["trail_offset"] > 0 and self.get_trail_price() > 0:
            trail_offset = self.get_exit_order()["trail_offset"]
            trail_price = self.get_trail_price()
            if self.get_position_size() > 0 and price - trail_offset < trail_price:
                logger.info(
                    f"Loss cut by trailing stop: {self.get_exit_order()['trail_offset']}"
                )
                self.close_all(self.get_exit_order()["trail_callback"])
            elif self.get_position_size() < 0 and price + trail_offset > trail_price:
                logger.info(
                    f"Loss cut by trailing stop: {self.get_exit_order()['trail_offset']}"
                )
                self.close_all(self.get_exit_order()["trail_callback"])

        if self.get_position_avg_price() > price:
            close_rate = (
                (self.get_position_avg_price() - price) / price - self.get_commission()
            ) * self.get_leverage()
            unrealised_pnl = -1 * self.get_position_size() * close_rate
        else:
            close_rate = (
                (price - self.get_position_avg_price()) / self.get_position_avg_price()
                - self.get_commission()
            ) * self.get_leverage()
            unrealised_pnl = self.get_position_size() * close_rate

        if unrealised_pnl < 0 and 0 < self.get_exit_order()["loss"] < abs(
            unrealised_pnl
        ):
            logger.info(f"Loss cut by stop loss: {self.get_exit_order()['loss']}")
            self.close_all(self.get_exit_order()["loss_callback"])

        if unrealised_pnl > 0 and 0 < self.get_exit_order()["profit"] < abs(
            unrealised_pnl
        ):
            logger.info(
                f"Take profit by stop profit: {self.get_exit_order()['profit']}"
            )
            self.close_all(self.get_exit_order()["profit_callback"])

    @staticmethod
    def override_strategy(strategy):
        def wrapper(self, action, open, close, high, low, volume):
            new_open_orders = []
            pos_size = self.get_position_size()
            trail_price = self.get_trail_price()

            self.OHLC = {"open": open, "high": high, "low": low, "close": close}

            if pos_size > 0 and low[-1] > trail_price:
                self.set_trail_price(low[-1])
            if pos_size < 0 and high[-1] < trail_price:
                self.set_trail_price(high[-1])

            index = 0

            while True:

                if index < len(self.open_orders):
                    order = self.open_orders[index]
                    index += 1
                else:
                    break

                id = order["id"]
                long = order["long"]
                qty = order["qty"]
                limit = order["limit"]
                stop = order["stop"]
                post_only = order["post_only"]
                reduce_only = order["reduce_only"]
                callback = order["callback"]

                if reduce_only and (
                    self.position_size == 0
                    or (long and pos_size > 0)
                    or (not long and pos_size < 0)
                ):
                    new_open_orders.append(
                        {
                            "id": id,
                            "long": long,
                            "qty": qty,
                            "limit": limit,
                            "stop": 0,
                            "post_only": post_only,
                            "reduce_only": reduce_only,
                            "callback": callback,
                        }
                    )
                    continue

                if limit > 0 and stop > 0 and (high[-1] >= stop >= low[-1]):
                    new_open_orders.append(
                        {
                            "id": id,
                            "long": long,
                            "qty": qty,
                            "limit": limit,
                            "stop": 0,
                            "post_only": post_only,
                            "reduce_only": reduce_only,
                            "callback": callback,
                        }
                    )
                    if not self.minute_granularity:
                        logger.info(
                            "Simulating Stop-Limit orders on historical bars can be erroneous "
                            + "as there is no way to guess intra-bar price movement. "
                            + "Stop-Limit orders are coverted into Limit orders "
                            + "once the stop is hit and evaluated in successive candles. "
                            + "Switch on Minute Granularity for a more accurate simulation of Stop-limit orders."
                        )
                    continue
                elif limit > 0:
                    if (long and low[-1] < limit) or (not long and high[-1] > limit):
                        self.commit(id, long, qty, limit, True, reduce_only, callback)
                        continue
                elif stop > 0:
                    if high[-1] >= stop >= low[-1]:
                        self.commit(id, long, qty, stop, True, reduce_only, callback)
                        continue

                new_open_orders.append(order)

            self.open_orders = new_open_orders

            if self.is_exit_order_active:
                self.eval_exit()

            if self.is_sltp_active:
                self.eval_sltp()

            return strategy(self, action, open, close, high, low, volume)

        return wrapper
