import logging
import os

import ccxt

from fasttrade.core.exchange import CryptoExchange
from fasttrade.core.telegrambot import TelegramBot
from fasttrade.core.tradeexcutor import TradeExecutor

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

    c_dir = os.path.dirname(__file__)
    with open(os.path.join(c_dir, "config/secrets.txt")) as key_file:
        api_key, secret, telegram_tkn, user_id = key_file.read().splitlines()

    ccxt_ex = ccxt.bitfinex()
    ccxt_ex.apiKey = api_key
    ccxt_ex.secret = secret

    exchange = CryptoExchange(ccxt_ex)
    trade_executor = TradeExecutor(exchange)
    telegram_bot = TelegramBot(telegram_tkn, user_id, trade_executor)

    telegram_bot.start_bot()
