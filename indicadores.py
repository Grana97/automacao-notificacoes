import requests
import pandas as pd
import ta

def get_klines(symbol, interval, limit=100):
    url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    candles = data['result']['list']
    df = pd.DataFrame(candles, columns=[
        "timestamp", "open", "high", "low", "close", "volume", "turnover"
    ])
    df["close"] = pd.to_numeric(df["close"])
    df["high"] = pd.to_numeric(df["high"])
    df["low"] = pd.to_numeric(df["low"])
    return df

def calcular_fibonacci(ultimo_preco):
    niveis = [0.236, 0.382, 0.5, 0.618, 0.786]
    return [round(ultimo_preco * (1 - n), 2) for n in niveis]

def analisar_ativos(ativo, timeframe):
    df = get_klines(ativo, timeframe)
    preco_atual = df["close"].iloc[-1]
    rsi = ta.momentum.RSIIndicator(df["close"]).rsi().iloc[-1]
    ema_50 = df["close"].ewm(span=50).mean().iloc[-1]
    ema_200 = df["close"].ewm(span=200).mean().iloc[-1]
    fib = calcular_fibonacci(preco_atual)

    alerta = None
    if rsi < 30:
        alerta = "RSI sobrevendido"
    elif rsi > 70:
        alerta = "RSI sobrecomprado"
    elif preco_atual > ema_50 > ema_200:
        alerta = "Tendência de alta"
    elif preco_atual < ema_50 < ema_200:
        alerta = "Tendência de baixa"

    return {
        "preco": round(preco_atual, 2),
        "rsi": round(rsi, 2),
        "ema_50": round(ema_50, 2),
        "ema_200": round(ema_200, 2),
        "fibonacci": fib,
        "alerta": alerta
    }
