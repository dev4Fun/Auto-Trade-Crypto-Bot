import abc


class TradeDetails(metaclass=abc.ABCMeta):
    def __init__(self, start_price: float, symbol: str, amount: float, currency: str = "USD"):
        self.start_price = start_price
        self.symbol = symbol.upper()
        self.amount = amount
        self.currency = currency

    @property
    def exchange_symbol(self):
        return f"{self.symbol.upper()}/{self.currency}"

    @property
    @abc.abstractmethod
    def exit_price(self):
        pass

    def __str__(self) -> str:
        return f"order for {self.amount} {self.exchange_symbol} with enter price: {self.start_price:.5}, " \
               f"exit_price: {self.exit_price:.5}"
