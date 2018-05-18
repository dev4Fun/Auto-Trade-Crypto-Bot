TITLES = ['idx', 'type', 'remaining', 'symbol', 'price']
SPACING = [4, 6, 8, 10, 8]


def format_open_orders(orders) -> str:
    def join_line(ln):
        return ' | '.join(str(item).center(SPACING[i]) for i, item in enumerate(ln))

    title_line = join_line(TITLES)
    lines = [title_line]
    for idx, order in enumerate(orders):
        line = [idx, order['side'], order['remaining'], order['symbol'], order['price']]
        lines.append(join_line(line))

    separator_line = '-' * len(title_line)
    return f"\n{separator_line}\n".join(lines)


def format_order(order):
    return f"{order['amount']} {order['symbol']} priced at {order['price']}"


def format_balance(balance) -> str:
    coin_balance_as_list = list(f"{coin}: {val}" for coin, val in balance.items())
    return "\n".join(coin_balance_as_list)

