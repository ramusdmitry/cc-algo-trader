# coding: UTF-8

import importlib
import json
import os
import sys
import textwrap

from src import query_yes_no
from src.config import config as conf


class BotFactory:

    @staticmethod
    def create(args):
        try:
            strategy_module = importlib.import_module("src.strategies." + args.strategy)
            cls = getattr(strategy_module, args.strategy)
            bot = cls()
            bot.test_net = args.demo
            bot.back_test = args.test
            bot.stub_test = args.stub
            bot.spot = args.spot
            bot.account = args.account
            bot.exchange_arg = args.exchange
            bot.pair = args.pair
            bot.plot = args.plot

            if conf["args"].html_report:
                STRATEGY_FILENAME = os.path.join(
                    os.getcwd(), f"src/strategies/{args.strategy}.py"
                )
                with open(STRATEGY_FILENAME, "r") as file:
                    original_content = file.read()

                updated_content = f"""
                #####################
                #
                # Command: {' '.join(sys.argv)}  
                #
                #####################
                """
                updated_content = textwrap.dedent(updated_content)

                updated_content = updated_content + original_content

                with open("html/data/strategy.py", "w") as file:
                    file.write(updated_content)

            if args.session is not None:
                try:
                    bot.session_file_name = args.session
                    bot.session_file = open(args.session, "r+")
                except Exception as e:
                    bot.session_file = open(args.session, "w")
                    raise e

                try:
                    vars = json.load(bot.session_file)

                    use_stored_session = query_yes_no(
                        "Session Found. Do you want to use it?", "no"
                    )
                    if use_stored_session:
                        bot.set_session(vars)
                except Exception as e:
                    raise e
                    
            else:
                bot.session_file = None

            return bot
        except Exception as _:
            raise Exception(f"Not Found Strategy : {args.strategy}")
