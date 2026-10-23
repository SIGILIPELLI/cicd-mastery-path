def total(prices, tax_rate=0.2):
    return round(sum(prices) * (1 + tax_rate), 2)
