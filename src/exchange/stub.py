from src import logger
from src.config import config as conf


class Stub:
    qty_in_usdt = False
    minute_granularity = False
    enable_trade_log = True
    balance = 1000
    leverage = 1

    def __init__(self):
        self.reset_state()
        self.order_log = open(conf["args"].order_log, "w")
        self.order_log.write("time,type,id,price,quantity,av_price,position,pnl,balance,drawdown\n")

    def reset_state(self):
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

    def get_lot(self):
        return float(self.get_balance() * self.get_leverage() / self.get_market_price())

    def get_balance(self):
        return self.balance

    def set_leverage(self, leverage):
        self.leverage = leverage

    def get_leverage(self):
        return self.leverage

    def get_position_size(self):
        return self.position_size

    def get_position_avg_price(self):
        return self.position_avg_price

    def get_pnl(self):
        entry_price = self.get_position_avg_price()
        pnl = (self.market_price - entry_price) * 100 / entry_price
        return pnl

    def cancel_all(self):
        self.open_orders = []

    def commit(self, id, long, qty, price, need_commission=False, reduce_only=False, callback=None):
        self.order_count += 1
        qty = abs(self.get_position_size()) if abs(qty) > abs(self.get_position_size()) and reduce_only else abs(qty)
        order_qty = qty if long else -qty
        next_qty = self.calculate_next_qty(order_qty)
        commission = self.get_commission() if need_commission else 0.0
        self.process_order_closing(order_qty, price, commission)
        self.position_size = self.get_position_size() + order_qty
        self.log_trade(long, id, price, order_qty, next_qty)

        if next_qty == 0 and callback:
            callback()

        self.update_position(next_qty, price, long, order_qty)
        if next_qty != 0 and callback:
            callback()

    def calculate_next_qty(self, order_qty):
        if self.get_position_size() * order_qty > 0:
            return self.get_position_size() + order_qty
        elif abs(order_qty) > abs(self.get_position_size()):
            return self.get_position_size() + order_qty
        else:
            return 0

    def process_order_closing(self, order_qty, price, commission):
        if (self.get_position_size() > 0 >= order_qty) or (self.get_position_size() < 0 < order_qty):
            closing_qty = -order_qty if abs(order_qty) < abs(self.get_position_size()) else self.get_position_size()
            close_rate = self.calculate_close_rate(price, commission)
            profit = abs(closing_qty) * close_rate * (1 if self.qty_in_usdt else self.get_position_avg_price())
            self.update_profit_and_loss(profit)
            self.update_drawdown()
            self.balance += profit
            self.update_balance_ath()

    def calculate_close_rate(self, price, commission):
        if self.get_position_size() >= 0:
            return ((price - self.get_position_avg_price()) / self.get_position_avg_price()) - commission
        else:
            return ((self.get_position_avg_price() - price) / self.get_position_avg_price()) - commission

    def update_profit_and_loss(self, profit):
        if profit > 0:
            self.win_profit += profit
            self.win_count += 1
        else:
            self.lose_loss += -profit
            self.lose_count += 1
            if self.calculate_close_rate * self.leverage < self.max_draw_down:
                self.max_draw_down = self.calculate_close_rate * self.leverage

    def update_drawdown(self):
        self.drawdown = (self.balance_ath - self.balance) / self.balance_ath * 100

    def update_balance_ath(self):
        if self.balance_ath < self.balance:
            self.balance_ath = self.balance
        if self.balance_ath > self.balance:
            current_drawdown = self.balance_ath - self.balance
            current_drawdown_perc = (self.balance_ath - self.balance) / self.balance_ath * 100
            if self.max_draw_down_session == 0:
                self.max_draw_down_session = current_drawdown
                self.max_draw_down_session_perc = current_drawdown_perc
            elif self.max_draw_down_session_perc < current_drawdown_perc:
                self.max_draw_down_session = current_drawdown
                self.max_draw_down_session_perc = current_drawdown_perc

    def log_trade(self, long, id, price, order_qty, next_qty):
        action = 'BUY' if long else 'SELL'
        trade_type = id if next_qty == 0 else 'Reversal'
        executed_qty = -self.position_size if abs(next_qty) else order_qty
        new_position_size = 0 if abs(next_qty) else self.position_size + order_qty
        close_rate = self.calculate_close_rate(price, 0.0)
        balance = self.get_balance()
        drawdown = self.drawdown

        log_entry = (
            f"{self.timestamp},{action},{trade_type},{price},{executed_qty},"
            f"{self.position_avg_price},{new_position_size},{close_rate:.2f},{balance:.2f},{drawdown:.2f}\n"
        )

        self.order_log.write(log_entry)
        self.order_log.flush()

        if self.enable_trade_log:
            self.log_trade_details(id, price, order_qty, next_qty, long)

    def log_trade_details(self, id, price, order_qty, next_qty, long):
        trade_info = {
            "ID": id if next_qty == 0 else "Reversal",
            "TIME": self.timestamp,
            "TRADE COUNT": self.order_count,
            "POSITION SIZE": self.position_size,
            "ENTRY PRICE": self.position_avg_price,
            "EXIT PRICE": price,
            "PROFIT": self.calculate_close_rate(price, 0.0),
            "BALANCE": self.get_balance(),
            "WIN RATE": 0 if self.order_count == 0 else self.win_count / (self.win_count + self.lose_count) * 100,
            "PROFIT FACTOR": self.win_profit if self.lose_loss == 0 else self.win_profit / self.lose_loss,
            "MAX DRAW DOWN": abs(self.max_draw_down) * 100,
            "MAX DRAW DOWN SESSION":
                f"{round(self.max_draw_down_session, 4)} or {round(self.max_draw_down_session_perc, 2)}%"
        }

        logger.info("========= Close Position =============")
        for key, value in trade_info.items():
            logger.info(f"{key:15}: {value}")
        logger.info("======================================")

    def update_position(self, next_qty, price, long, order_qty):
        if next_qty != 0:
            if self.enable_trade_log:
                self.log_new_position(price, order_qty, next_qty, long)

            self.update_avg_price(price, next_qty, long, order_qty)
            self.position_size = next_qty
            self.log_current_position(next_qty)

            self.set_trail_price(price)

    def log_new_position(self, price, order_qty, next_qty, long):
        logger.info("********* Create Position ************")
        logger.info(f"TIME          : {self.timestamp}")
        logger.info(f"PRICE         : {price}")
        logger.info(f"TRADE COUNT   : {self.order_count}")
        logger.info(f"ID            : {order_qty}")
        logger.info(f"POSITION SIZE : {order_qty if next_qty * self.position_size > 0 else next_qty}")
        logger.info("**************************************")

    def update_avg_price(self, price, next_qty, long, order_qty):
        if long and 0 < self.position_size < next_qty:
            self.position_avg_price = (self.position_avg_price * self.position_size + price * order_qty) / next_qty
        elif not long and 0 > self.position_size > next_qty:
            self.position_avg_price = (self.position_avg_price * self.position_size - price * order_qty) / next_qty
        else:
            self.position_avg_price = price

    def log_current_position(self, next_qty):
        logger.info("//////// Current Position ////////////")
        logger.info(f"current position size: {next_qty} at avg. price: {self.position_avg_price}")

    def eval_exit(self):
        if self.get_position_size() == 0:
            return

        price = self.get_market_price()
        self.check_trailing_stop(price)
        self.check_stop_loss(price)
        self.check_take_profit(price)

    def check_trailing_stop(self, price):
        if self.get_exit_order()["trail_offset"] > 0 and self.get_trail_price() > 0:
            trail_offset = self.get_exit_order()["trail_offset"]
            trail_price = self.get_trail_price()
            if self.get_position_size() > 0 and price - trail_offset < trail_price:
                logger.info(f"Loss cut by trailing stop: {trail_offset}")
                self.close_all(self.get_exit_order()["trail_callback"])
            elif self.get_position_size() < 0 and price + trail_offset > trail_price:
                logger.info(f"Loss cut by trailing stop: {trail_offset}")
                self.close_all(self.get_exit_order()["trail_callback"])

    def check_stop_loss(self, price):
        avg_price = self.get_position_avg_price()
        commission = self.get_commission()
        leverage = self.get_leverage()
        pos_size = self.get_position_size()
        if self.get_position_avg_price() > price:
            close_rate = ((avg_price - price) / price - commission) * leverage
            unrealised_pnl = -1 * pos_size * close_rate
        else:
            close_rate = ((price - avg_price) / avg_price - commission) * leverage
            unrealised_pnl = pos_size * close_rate

        if unrealised_pnl < 0 and 0 < self.get_exit_order()["loss"] < abs(unrealised_pnl):
            logger.info(f"Loss cut by stop loss: {self.get_exit_order()['loss']}")
            self.close_all(self.get_exit_order()["loss_callback"])

    def check_take_profit(self, price):
        unrealised_pnl = self.calculate_unrealised_pnl(price)
        if unrealised_pnl > 0 and 0 < self.get_exit_order()["profit"] < abs(unrealised_pnl):
            logger.info(f"Take profit by stop profit: {self.get_exit_order()['profit']}")
            self.close_all(self.get_exit_order()["profit_callback"])

    def calculate_unrealised_pnl(self, price):
        avg_price = self.get_position_avg_price()
        commission = self.get_commission()
        leverage = self.get_leverage()
        pos_size = self.get_position_size()
        if avg_price > price:
            close_rate = ((avg_price - price) / price - commission) * leverage
            return -1 * pos_size * close_rate
        else:
            close_rate = ((price - avg_price) / avg_price - commission) * leverage
            return pos_size * close_rate

    def eval_sltp(self):
        pos_size = self.get_position_size()
        if pos_size == 0:
            return

        best_bid = self.market_price
        best_ask = self.market_price
        tp_percent_long = self.get_sltp_values()["profit_long"]
        tp_percent_short = self.get_sltp_values()["profit_short"]
        avg_entry = self.get_position_avg_price()
        sl_percent_long = self.get_sltp_values()["stop_long"]
        sl_percent_short = self.get_sltp_values()["stop_short"]

        self.check_stop_loss_long(pos_size, sl_percent_long, avg_entry)
        self.check_stop_loss_short(pos_size, sl_percent_short, avg_entry)

        if self.should_evaluate_tp_next_candle():
            return

        self.check_take_profit_long(pos_size, tp_percent_long, avg_entry, best_ask)
        self.check_take_profit_short(pos_size, tp_percent_short, avg_entry, best_bid)

    def check_stop_loss_long(self, pos_size, sl_percent_long, avg_entry):
        if sl_percent_long > 0 and pos_size > 0:
            sl_price_long = round(avg_entry - (avg_entry * sl_percent_long), self.quote_rounding)
            if self.OHLC["low"][-1] <= sl_price_long:
                self.close_all_at_price(sl_price_long, self.get_sltp_values()["stop_long_callback"])

    def check_stop_loss_short(self, pos_size, sl_percent_short, avg_entry):
        if sl_percent_short > 0 and pos_size < 0:
            sl_price_short = round(avg_entry + (avg_entry * sl_percent_short), self.quote_rounding)
            if self.OHLC["high"][-1] >= sl_price_short:
                self.close_all_at_price(sl_price_short, self.get_sltp_values()["stop_short_callback"])

    def should_evaluate_tp_next_candle(self):
        exp1 = (self.isLongEntry[-1] and not self.isLongEntry[-2] and self.get_sltp_values()["eval_tp_next_candle"])
        exp2 = (self.isShortEntry[-1] and not self.isShortEntry[-2] and self.get_sltp_values()["eval_tp_next_candle"])
        return (exp1 or exp2)

    def check_take_profit_long(self, pos_size, tp_percent_long, avg_entry, best_ask):
        if tp_percent_long > 0 and pos_size > 0:
            tp_price_long = round(avg_entry + (avg_entry * tp_percent_long), self.quote_rounding)
            if self.tp_price_conditions_met(tp_price_long, best_ask):
                tp_price_long = best_ask
            if self.OHLC["high"][-1] >= tp_price_long:
                self.close_all_at_price(tp_price_long, self.get_sltp_values()["profit_long_callback"])

    def check_take_profit_short(self, pos_size, tp_percent_short, avg_entry, best_bid):
        if tp_percent_short > 0 and pos_size < 0:
            tp_price_short = round(avg_entry - (avg_entry * tp_percent_short), self.quote_rounding)
            if self.tp_price_conditions_met(tp_price_short, best_bid):
                tp_price_short = best_bid
            if self.OHLC["low"][-1] <= tp_price_short:
                self.close_all_at_price(tp_price_short, self.get_sltp_values()["profit_short_callback"])

    def tp_price_conditions_met(self, tp_price, best_price):
        return (tp_price <= best_price
                and self.get_sltp_values()["eval_tp_next_candle"]
                and (not self.isLongEntry[-1] and self.isLongEntry[-2] and not self.isLongEntry[-3]))

    @staticmethod
    def override_strategy(strategy):
        def wrapper(self, action, open, close, high, low, volume):
            self.update_OHLC(open, high, low, close)
            self.update_trail_price(low, high)
            self.process_open_orders(open, high, low)

            if self.is_exit_order_active:
                self.eval_exit()

            if self.is_sltp_active:
                self.eval_sltp()

            return strategy(self, action, open, close, high, low, volume)

        return wrapper

    def update_OHLC(self, open, high, low, close):
        self.OHLC = {"open": open, "high": high, "low": low, "close": close}

    def update_trail_price(self, low, high):
        pos_size = self.get_position_size()
        trail_price = self.get_trail_price()

        if pos_size > 0 and low[-1] > trail_price:
            self.set_trail_price(low[-1])
        if pos_size < 0 and high[-1] < trail_price:
            self.set_trail_price(high[-1])

    def process_open_orders(self, open, high, low):
        new_open_orders = []
        for order in self.open_orders:
            if self.should_reduce_only_order(order, high, low):
                new_open_orders.append(self.convert_to_limit_order(order))
                continue

            if self.is_limit_order_triggered(order, high, low):
                new_open_orders.append(self.convert_to_limit_order(order))
                continue

            if self.is_stop_order_triggered(order, high, low):
                self.commit(order["id"], order["long"], order["qty"], order["stop"], True,
                            order["reduce_only"], order["callback"])
                continue

            new_open_orders.append(order)

        self.open_orders = new_open_orders

    def should_reduce_only_order(self, order, high, low):
        pos_size = self.get_position_size()
        exp = (pos_size == 0 or (order["long"] and pos_size > 0) or (not order["long"] and pos_size < 0))
        return order["reduce_only"] and exp

    def convert_to_limit_order(self, order):
        return {
            "id": order["id"],
            "long": order["long"],
            "qty": order["qty"],
            "limit": order["limit"],
            "stop": 0,
            "post_only": order["post_only"],
            "reduce_only": order["reduce_only"],
            "callback": order["callback"],
        }

    def is_limit_order_triggered(self, order, high, low):
        exp1 = (order["long"] and low[-1] < order["limit"])
        exp2 = (not order["long"] and high[-1] > order["limit"])
        return order["limit"] > 0 and (exp1 or exp2)

    def is_stop_order_triggered(self, order, high, low):
        return order["stop"] > 0 and (high[-1] >= order["stop"] >= low[-1])
