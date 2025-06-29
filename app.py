import os
import time
import requests
import schedule
import pandas as pd
import datetime
import matplotlib.pyplot as plt
from flask import Flask
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from padroes import detectar_oco, detectar_triangulo, detectar_cunha

app = Flask(__name__)

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = ["BTCUSDT", "ETHUSDT", "AAVEUSDT", "XRPUSDT", "SOLUSDT", "WIFUSDT", "AEROUSDT", "HYPEUSDT"]
TIMEFRAMES = {
    "15m": "15",
    "1h": "60",
    "4h": "240"
}

def get_klines(symbol, interval):
    url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval={interval}&limit=200"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()["result"]["list"]
        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
        df.set_index("timestamp", inplace=True)
        df = df.astype(float)
        return df
    except Exception as e:
        print(f"Erro ao buscar dados de {symbol} [{interval}]: {e}")
        return None

def calculate_indicators(df):
    rsi = RSIIndicator(close=df["close"], window=14).rsi()
    ema9 = EMAIndicator(close=df["close"], window=9).ema_indicator()
    ema21 = EMAIndicator(close=df["close"], window=21).ema_indicator()
    ema50 = EMAIndicator(close=df["close"], window=50).ema_indicator()
    ema200 = EMAIndicator(close=df["close"], window=200).ema_indicator()
    return rsi, ema9, ema21, ema50, ema200

def generate_chart(df, symbol, tf):
    plt.figure(figsize=(10, 4))
    plt.plot(df["close"], label="Preço")
    plt.plot(EMAIndicator(close=df["close"], window=9).ema_indicator(), label="EMA 9")
    plt.plot(EMAIndicator(close=df["close"], window=21).ema_indicator(), label="EMA 21")
    plt.plot(EMAIndicator(close=df["close"], window=50).ema_indicator(), label="EMA 50")
    plt.plot(EMAIndicator(close=df["close"], window=200).ema_indicator(), label="EMA 200")
    plt.title(f"{symbol} - {tf}")
    plt.legend()
    filename = f"{symbol}_{tf}_chart.png"
    plt.savefig(filename)
    plt.close()
    return filename

def send_discord(msg, img_path=None):
    data = {"content": msg}
    files = {"file": open(img_path, "rb")} if img_path else None
    try:
        requests.post(DISCORD_WEBHOOK, data=data, files=files)
    except Exception as e:
        print("Erro Discord:", e)

def send_telegram(msg, img_path=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
        if img_path:
            img_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            files = {"photo": open(img_path, "rb")}
            requests.post(img_url, data={"chat_id": TELEGRAM_CHAT_ID}, files=files)
    except Exception as e:
        print("Erro Telegram:", e)

def build_summary(symbol, tf, df, rsi, ema9, ema21, ema50, ema200):
    last_price = df["close"].iloc[-1]
    last_rsi = rsi.iloc[-1]
    text = f"🕒 {symbol} - {tf} \n"
    text += f"💰 Preço: {last_price:.2f} | RSI: {last_rsi:.2f}\n"
    text += f"📉 EMA9: {ema9.iloc[-1]:.2f} | EMA21: {ema21.iloc[-1]:.2f} | EMA50: {ema50.iloc[-1]:.2f} | EMA200: {ema200.iloc[-1]:.2f}\n"

    if last_rsi >= 70:
        text += "⚠️ RSI em sobrecompra!\n"
    elif last_rsi <= 30:
        text += "⚠️ RSI em sobrevenda!\n"

    if ema9.iloc[-2] < ema21.iloc[-2] and ema9.iloc[-1] > ema21.iloc[-1]:
        text += "✅ Cruzamento de Alta (EMA 9 > EMA 21)\n"
    elif ema9.iloc[-2] > ema21.iloc[-2] and ema9.iloc[-1] < ema21.iloc[-1]:
        text += "⚠️ Cruzamento de Baixa (EMA 9 < EMA 21)\n"

    if ema50.iloc[-2] < ema200.iloc[-2] and ema50.iloc[-1] > ema200.iloc[-1]:
        text += "🚀 Golden Cross\n"
    elif ema50.iloc[-2] > ema200.iloc[-2] and ema50.iloc[-1] < ema200.iloc[-1]:
        text += "🛑 Death Cross\n"

    oco = detectar_oco(df)
    triangulo = detectar_triangulo(df)
    cunha = detectar_cunha(df)

    if oco: text += oco + "\n"
    if triangulo: text += triangulo + "\n"
    if cunha: text += cunha + "\n"

    return text

def analyze_all():
    print("📊 Iniciando análise múltiplos timeframes...")
    for symbol in SYMBOLS:
        for tf_name, interval in TIMEFRAMES.items():
            df = get_klines(symbol, interval)
            if df is not None:
                rsi, ema9, ema21, ema50, ema200 = calculate_indicators(df)
                resumo = build_summary(symbol, tf_name, df, rsi, ema9, ema21, ema50, ema200)
                chart = generate_chart(df, symbol, tf_name)
                send_discord(resumo, chart)
                send_telegram(resumo, chart)

schedule.every().hour.do(analyze_all)

@app.route("/")
def status():
    return "✅ Bot Multi-Timeframe rodando!"

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    import threading
    threading.Thread(target=run_scheduler).start()
    app.run(host="0.0.0.0", port=10000)



