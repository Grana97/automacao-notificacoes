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
    levels = {
        "0.236": round(high - 0.236 * diff, 2),
        "0.382": round(high - 0.382 * diff, 2),
        "0.5": round(high - 0.5 * diff, 2),
        "0.618": round(high - 0.618 * diff, 2),
        "0.786": round(high - 0.786 * diff, 2)
    }
    return levels

def buscar_dados(symbol, interval="1h", limit=200):
    try:
        url = f"{BINANCE_URL}?symbol={symbol}&interval={interval}&limit={limit}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        closes = [float(k[4]) for k in data]
        highs = [float(k[2]) for k in data]
        lows = [float(k[3]) for k in data]
        return closes, highs, lows
    except Exception as e:
        print(f"Erro buscando dados de {symbol} - {interval}: {e}")
        return [], [], []

def analisar():
    global last_notification_time, last_hourly_summary_time

    agora = datetime.now()
    resumo = f"📊 **Resumo {agora.strftime('%H:%M')}**\n\n"
    alerts = []

    for symbol in CRYPTO_SYMBOLS:
        closes, highs, lows = buscar_dados(symbol, "1h")
        if not closes: continue

        price = closes[-1]
        rsi = calcular_rsi(closes)
        ema_12 = calcular_ema(closes[-12:], 12)
        ema_26 = calcular_ema(closes[-26:], 26)
        ema_200 = calcular_ema(closes[-200:], 200)
        fibo = calcular_fibonacci(max(highs), min(lows))

        direcao = "📈" if price > ema_12 > ema_26 else "📉" if price < ema_12 < ema_26 else "🔄"
        status = f"{direcao} **{symbol}**\n💰Preço: ${price:.2f}\n📊 RSI: {rsi}\n📉 EMAs: 12={ema_12}, 26={ema_26}, 200={ema_200}\n🔢 Fibonacci: {fibo['0.236']} / {fibo['0.5']} / {fibo['0.618']}\n"
        resumo += status + "\n"

        if abs(rsi - 50) > 20:
            key = f"{symbol}_rsi_{int(agora.timestamp()) // 900}"
            if key not in last_notification_time:
                alerta = f"🚨 Alerta {symbol} RSI: {rsi} | Preço: ${price:.2f}"
                alerts.append(alerta)
                last_notification_time[key] = agora

    for alert in alerts:
        enviar_discord(alert)
        enviar_telegram(alert)
        print(f"🔔 Alerta: {alert}")
        app_status["ultima_notificacao"] = alert
        app_status["total_notificacoes"] += 1

    if not last_hourly_summary_time or (agora - last_hourly_summary_time).seconds >= 3600:
        enviar_discord(resumo)
        enviar_telegram(resumo)
        last_hourly_summary_time = agora
        app_status["ultima_notificacao"] = f"Resumo {agora.strftime('%H:%M')}"
        app_status["total_notificacoes"] += 1
        print("📬 Resumo horário enviado")

@app.route('/')
def home():
    return f"""
    <h1>Bot Cripto Ativo</h1>
    <p>Status: {app_status['status']}</p>
    <p>Iniciado: {app_status['iniciado_em']}</p>
    <p>Última: {app_status['ultima_notificacao']}</p>
    <p>Total: {app_status['total_notificacoes']}</p>
    """

@app.route('/status')
def status():
    return jsonify(app_status)

@app.route('/test')
def test():
    msg = f"🧪 Teste do bot às {datetime.now().strftime('%H:%M:%S')}"
    enviar_discord(msg)
    enviar_telegram(msg)
    return jsonify({"status": "enviado", "hora": datetime.now().strftime('%H:%M:%S')})

def agendar():
    schedule.every(5).minutes.do(analisar)
    while True:
        schedule.run_pending()
        time.sleep(30)

def keep_alive():
    url = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:5000")
    while True:
        try:
            requests.get(f"{url}/status")
            print("✅ Keep-alive")
        except:
            print("❌ Falha Keep-alive")
        time.sleep(300)

if __name__ == "__main__":
    print("🚀 Bot iniciado!")
    Thread(target=agendar, daemon=True).start()
    Thread(target=keep_alive, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
