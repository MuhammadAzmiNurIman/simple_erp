from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal('0.01')
FOUR_PLACES = Decimal('0.0001')


def decimal_value(value):
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value if value is not None else 0))


def quantize_money(value):
    return decimal_value(value).quantize(CENT, rounding=ROUND_HALF_UP)


def quantize_cost(value):
    return decimal_value(value).quantize(FOUR_PLACES, rounding=ROUND_HALF_UP)


def money_json(value):
    return float(quantize_money(value))


def cost_json(value):
    return float(quantize_cost(value))
