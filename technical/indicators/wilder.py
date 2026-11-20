"""Wilder's moving average seeded with a simple average."""


def wilder_average(values, period):
    if len(values) < period:
        return None
    average = sum(values.iloc[:period]) / period
    for value in values.iloc[period:]:
        average += (value - average) / period
    return float(average)
