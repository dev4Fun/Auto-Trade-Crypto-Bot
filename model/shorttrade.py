from model.trade import TradeDetails


class ShortTrade(TradeDetails):
    def __init__(self, start_price: float, symbol: str, amount: float, percent_change: float = 0.5,
                 currency: str = "USD") -> None:
        super().__init__(start_price, symbol, amount, currency)
        self.end_price = start_price * (1 - percent_change / 100)

    @property
    def exit_price(self):
        return self.end_price

    def __str__(self) -> str:
        return "Short " + super().__str__()
