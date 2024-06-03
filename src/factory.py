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
            strategy_module = importlib.import_module(f"src.strategies.{args.strategy}")
            cls = getattr(strategy_module, args.strategy)
            bot = cls()
            BotFactory._initialize_bot(bot, args)

            if conf["args"].html_report:
                BotFactory._generate_html_report(args.strategy)

            if args.session is not None:
                BotFactory._handle_session(bot, args.session)

            return bot
        except Exception as e:
            raise Exception(f"Strategy Not Found: {args.strategy}") from e

    @staticmethod
    def _initialize_bot(bot, args):
        bot.test_net = args.demo
        bot.back_test = args.test
        bot.stub_test = args.stub
        bot.spot = args.spot
        bot.account = args.account
        bot.exchange_arg = args.exchange
        bot.pair = args.pair
        bot.plot = args.plot

    @staticmethod
    def _generate_html_report(strategy_name):
        strategy_file_path = os.path.join(os.getcwd(), f"src/strategies/{strategy_name}.py")
        with open(strategy_file_path, "r") as file:
            original_content = file.read()

        command_info = textwrap.dedent(f"""
        #####################
        #
        # Command: {' '.join(sys.argv)}
        #
        #####################
        """)

        updated_content = command_info + original_content

        with open("html/data/strategy.py", "w") as file:
            file.write(updated_content)

    @staticmethod
    def _handle_session(bot, session_file_name):
        try:
            bot.session_file_name = session_file_name
            bot.session_file = open(session_file_name, "r+")
        except Exception:
            bot.session_file = open(session_file_name, "w")
            raise

        try:
            session_vars = json.load(bot.session_file)
            use_stored_session = query_yes_no("Session Found. Do you want to use it?", "no")
            if use_stored_session:
                bot.set_session(session_vars)
        except Exception as e:
            raise e
        else:
            bot.session_file = None
