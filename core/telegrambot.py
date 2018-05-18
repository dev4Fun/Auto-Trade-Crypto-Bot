import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, \
    ConversationHandler, MessageHandler, BaseFilter, run_async, Filters

from fasttrade.core.tradeexcutor import TradeExecutor
from fasttrade.model.longtrade import LongTrade
from fasttrade.model.shorttrade import ShortTrade
from fasttrade.util import formatter

TRADE_SELECT = "trade_select"
SHORT_TRADE = "short_trade"
LONG_TRADE = "long_trade"
OPEN_ORDERS = "open_orders"
FREE_BALANCE = "free_balance"

CANCEL_ORD = "cancel_order"
PROCESS_ORD_CANCEL = "process_ord_cancel"

COIN_NAME = "coin_name"
PERCENT_CHANGE = "percent_select"
AMOUNT = "amount"
PRICE = "price"
PROCESS_TRADE = "process_trade"

CONFIRM = "confirm"
CANCEL = "cancel"
END_CONVERSATION = ConversationHandler.END


class TelegramBot:
    class PrivateUserFiler(BaseFilter):
        def __init__(self, user_id):
            self.user_id = int(user_id)

        def filter(self, message):
            return message.from_user.id == self.user_id

    def __init__(self, token: str, allowed_user_id, trade_executor: TradeExecutor):
        self.updater = Updater(token=token)
        self.dispatcher = self.updater.dispatcher
        self.trade_executor = trade_executor
        self.exchange = self.trade_executor.exchange
        self.private_filter = self.PrivateUserFiler(allowed_user_id)
        self._prepare()

    def _prepare(self):

        # Create our handlers

        def show_help(bot, update):
            update.effective_message.reply_text('Type /trade to show options')

        def show_options(bot, update):
            button_list = [
                [InlineKeyboardButton("Short trade", callback_data=SHORT_TRADE),
                 InlineKeyboardButton("Long trade", callback_data=LONG_TRADE), ],
                [InlineKeyboardButton("Open orders", callback_data=OPEN_ORDERS),
                 InlineKeyboardButton("Available balance", callback_data=FREE_BALANCE)],
            ]

            update.message.reply_text("Trade options:", reply_markup=InlineKeyboardMarkup(button_list))
            return TRADE_SELECT

        def process_trade_selection(bot, update, user_data):
            query = update.callback_query
            selection = query.data

            if selection == OPEN_ORDERS:
                orders = self.exchange.fetch_open_orders()

                if len(orders) == 0:
                    bot.edit_message_text(text="You don't have open orders",
                                          chat_id=query.message.chat_id,
                                          message_id=query.message.message_id)
                    return END_CONVERSATION

                # show the option to cancel active orders
                keyboard = [
                    [InlineKeyboardButton("Ok", callback_data=CONFIRM),
                     InlineKeyboardButton("Cancel order", callback_data=CANCEL)]
                ]

                bot.edit_message_text(text=formatter.format_open_orders(orders),
                                      chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      reply_markup=InlineKeyboardMarkup(keyboard))

                # attach opened orders, so that we can cancel by index
                user_data[OPEN_ORDERS] = orders
                return CANCEL_ORD

            elif selection == FREE_BALANCE:
                balance = self.exchange.free_balance

                msg = "You don't have any available balance" if len(balance) == 0 \
                    else f"Your available balance:\n{formatter.format_balance(balance)}"

                bot.edit_message_text(text=msg,
                                      chat_id=query.message.chat_id,
                                      message_id=query.message.message_id)
                return END_CONVERSATION

            user_data[TRADE_SELECT] = selection
            bot.edit_message_text(text=f'Enter coin name for {selection}',
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id)
            return COIN_NAME

        def cancel_order(bot, update):
            query = update.callback_query

            if query.data == CANCEL:
                query.message.reply_text('Enter order index to cancel: ')
                return PROCESS_ORD_CANCEL

            show_help(bot, update)
            return END_CONVERSATION

        def process_order_cancel(bot, update, user_data):
            idx = int(update.message.text)
            order = user_data[OPEN_ORDERS][idx]
            self.exchange.cancel_order(order['id'])
            update.message.reply_text(f'Canceled order: {formatter.format_order(order)}')
            return END_CONVERSATION

        def process_coin_name(bot, update, user_data):
            user_data[COIN_NAME] = update.message.text.upper()
            update.message.reply_text(f'What amount of {user_data[COIN_NAME]}')
            return AMOUNT

        def process_amount(bot, update, user_data):
            user_data[AMOUNT] = float(update.message.text)
            update.message.reply_text(f'What % change for {user_data[AMOUNT]} {user_data[COIN_NAME]}')
            return PERCENT_CHANGE

        def process_percent(bot, update, user_data):
            user_data[PERCENT_CHANGE] = float(update.message.text)
            update.message.reply_text(f'What price for 1 unit of {user_data[COIN_NAME]}')
            return PRICE

        def process_price(bot, update, user_data):
            user_data[PRICE] = float(update.message.text)

            keyboard = [
                [InlineKeyboardButton("Confirm", callback_data=CONFIRM),
                 InlineKeyboardButton("Cancel", callback_data=CANCEL)]
            ]

            update.message.reply_text(f"Confirm the trade: '{TelegramBot.build_trade(user_data)}'",
                                      reply_markup=InlineKeyboardMarkup(keyboard))

            return PROCESS_TRADE

        def process_trade(bot, update, user_data):
            query = update.callback_query

            if query.data == CONFIRM:
                trade = TelegramBot.build_trade(user_data)
                self._execute_trade(trade)
                update.callback_query.message.reply_text(f'Scheduled: {trade}')
            else:
                show_help(bot, update)

            return END_CONVERSATION

        def handle_error(bot, update, error):
            logging.warning('Update "%s" caused error "%s"', update, error)
            update.message.reply_text(f'Unexpected error:\n{error}')

        # configure our handlers
        def build_conversation_handler():
            entry_handler = CommandHandler('trade', filters=self.private_filter, callback=show_options)
            conversation_handler = ConversationHandler(
                entry_points=[entry_handler],
                fallbacks=[entry_handler],
                states={
                    TRADE_SELECT: [CallbackQueryHandler(process_trade_selection, pass_user_data=True)],
                    CANCEL_ORD: [CallbackQueryHandler(cancel_order)],
                    PROCESS_ORD_CANCEL: [MessageHandler(filters=Filters.text, callback=process_order_cancel, pass_user_data=True)],
                    COIN_NAME: [MessageHandler(filters=Filters.text, callback=process_coin_name, pass_user_data=True)],
                    AMOUNT: [MessageHandler(Filters.text, callback=process_amount, pass_user_data=True)],
                    PERCENT_CHANGE: [MessageHandler(Filters.text, callback=process_percent, pass_user_data=True)],
                    PRICE: [MessageHandler(Filters.text, callback=process_price, pass_user_data=True)],
                    PROCESS_TRADE: [CallbackQueryHandler(process_trade, pass_user_data=True)],
                },
            )
            return conversation_handler

        self.dispatcher.add_handler(CommandHandler('start', filters=self.private_filter, callback=show_help))
        self.dispatcher.add_handler(build_conversation_handler())
        self.dispatcher.add_error_handler(handle_error)

    def start_bot(self):
        self.updater.start_polling()

    @run_async
    def _execute_trade(self, trade):
        loop = asyncio.new_event_loop()
        task = loop.create_task(self.trade_executor.execute_trade(trade))
        loop.run_until_complete(task)

    @staticmethod
    def build_trade(user_data):
        current_trade = user_data[TRADE_SELECT]
        price = user_data[PRICE]
        coin_name = user_data[COIN_NAME]
        amount = user_data[AMOUNT]
        percent_change = user_data[PERCENT_CHANGE]

        if current_trade == LONG_TRADE:
            return LongTrade(price, coin_name, amount, percent_change)
        elif current_trade == SHORT_TRADE:
            return ShortTrade(price, coin_name, amount, percent_change)
        else:
            raise NotImplementedError
