import time
import requests
import os
from flask import Flask, jsonify
from threading import Thread
from datetime import datetime
import schedule
import pandas as pd
import ta

app = Flask(__name__)

app_status = {
    "iniciado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "ultima_notificacao": "Nenhuma ainda",
    "total_notificacoes": 0,
    "status": "Rodando"
}

CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AAVEUSDT", "XRPUSDT", "WIFUSDT", "AEROUSDT", "HYPEUSDT"]
BYBIT_URL = "https://api.bybit.com/v5/market/kline"
last_notification_time = {}

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

def enviar_discord(mensagem):
    if not DISCORD_WEBHOOK:
        print("❌ Webhook Discord não configurado")
        return False
    try:
        response = requests.post(DISCORD_WEBHOOK, json={"content": mensagem}, timeout=10)
        return response.status_code in [200, 204]
    except Exception as e:
        print(f"Erro Discord: {e}")
        return False

def enviar_telegram(mensagem):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram não configurado")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        response = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": mensagem})
        return response.status_code == 200
    except Exception as e:
        print(f"Erro Telegram: {e}")
        return False

def buscar_dados(symbol, interval="60", limit=100):
    try:
        url = f"{BYBIT_URL}?category=linear&symbol={symbol}&interval={interval}&limit={limit}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json().get("result", {}).get("list", [])
        if not data:
            raise ValueError("Sem dados retornados")
        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
        df["close"] = df["close"].astype(float)
        return df
    except Exception as e:
        print(f"Erro ao buscar dados de {symbol}: {e}")
        return pd.DataFrame()

def calcular_indicadores(df):
    if df.empty or len(df) < 30:
        return 0, 0, 0
    rsi = ta.momentum.RSIIndicator(close=df["close"], window=14).rsi().iloc[-1]
    ema9 = ta.trend.EMAIndicator(close=df["close"], window=9).ema_indicator().iloc[-1]
    ema21 = ta.trend.EMAIndicator(close=df["close"], window=21).ema_indicator().iloc[-1]
    return round(rsi, 2), round(ema9, 2), round(ema21, 2)

def enviar_resumo():
    mensagem = "📊 *Resumo de Mercado (Bybit)* 📊\n"
    for symbol in CRYPTO_SYMBOLS:
        df = buscar_dados(symbol)
        if df.empty:
            continue
        preco = round(df["close"].iloc[-1], 2)
        rsi, ema9, ema21 = calcular_indicadores(df)
        mensagem += f"\n*{symbol.replace('USDT', '')}*: ${preco} | RSI: {rsi} | EMA9: {ema9} | EMA21: {ema21}"
    enviar_discord(mensagem)
    enviar_telegram(mensagem)
    app_status["ultima_notificacao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    app_status["total_notificacoes"] += 1

def verificar_alertas():
    for symbol in CRYPTO_SYMBOLS:
        df = buscar_dados(symbol)
        if df.empty:
            continue
        preco = round(df["close"].iloc[-1], 2)
        rsi, ema9, ema21 = calcular_indicadores(df)
        alerta = ""
        if rsi < 30:
            alerta += f"🔻 RSI abaixo de 30 em {symbol}!"
        elif rsi > 70:
            alerta += f"🚀 RSI acima de 70 em {symbol}!"
        if preco > ema9 > ema21:
            alerta += f" 📈 Tendência de alta (Preço > EMA9 > EMA21)"
        elif preco < ema9 < ema21:
            alerta += f" 📉 Tendência de baixa (Preço < EMA9 < EMA21)"
        if alerta:
            mensagem = f"⚠️ Alerta para {symbol}:\nPreço: ${preco} | RSI: {rsi} | EMA9: {ema9} | EMA21: {ema21}\n{alerta}"
            enviar_discord(mensagem)
            enviar_telegram(mensagem)

def agendador():
    schedule.every(1).hours.do(enviar_resumo)
    while True:
        schedule.run_pending()
        verificar_alertas()
        time.sleep(60)

@app.route("/status", methods=["GET"])
def status():
    return jsonify(app_status)

@app.route("/", methods=["GET"])
def home():
    return "🚀 Bot com Bybit iniciado!"

if __name__ == "__main__":
    print("🚀 Bot com Bybit iniciado!")
    thread = Thread(target=agendador)
    thread.daemon = True
    thread.start()
    app.run(host="0.0.0.0", port=10000)



