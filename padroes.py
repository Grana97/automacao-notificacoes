import pandas as pd

def detectar_oco(df):
    if len(df) < 5:
        return False
    h1 = df['high'].iloc[-5]
    h2 = df['high'].iloc[-3]
    h3 = df['high'].iloc[-1]
    if h2 > h1 and h2 > h3 and abs(h1 - h3) / h2 < 0.03:
        return True
    return False

def detectar_triangulo(df):
    if len(df) < 10:
        return False
    topos = df['high'].rolling(window=5).max()
    fundos = df['low'].rolling(window=5).min()
    if topos.is_monotonic_decreasing and fundos.is_monotonic_increasing:
        return True
    return False

def detectar_cunha(df):
    if len(df) < 10:
        return False
    delta_highs = df['high'].diff().dropna()
    delta_lows = df['low'].diff().dropna()
    if delta_highs.mean() < 0 and delta_lows.mean() > 0:
        return True
    return False
