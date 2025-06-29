import time
import requests
import os
from flask import Flask, jsonify
from threading import Thread
import schedule
from datetime import datetime
import math

app = Flask(__name__)

app_status = {
    "iniciado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "ultima_notificacao": "Nenhuma ainda",
    "total_notificacoes": 0,
    "status": "Rodando"
}

CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT", "AAVEUSDT", "XRPUSDT"]
BINANCE_URL = "https://api.binance.com/api/v3/klines"
last_notification_time = {}
last_hourly_summary_time = None

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
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

def calcular_rsi(prices):
    if len(prices) < 15:
        return 50
    gains = []
    losses = []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i-1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains[-14:]) / 14
    avg_loss = sum(losses[-14:]) / 14
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

def calcular_ema(prices, period):
    k = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = price * k + ema * (1 - k)
    return round(ema, 2)

def calcular_fibonacci(high, low):
    diff = high - low
    levels
