import os
import time
import threading
import requests
import pandas as pd
import schedule
from flask import Flask, jsonify
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from padroes import detectar_oco, detectar_triangulo, detectar_cunha
import matplotlib.pyplot as plt

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:10000")

symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AAVEUSDT", "XRPUSDT", "HYPEUSDT", "WIFUSDT", "AEROUSDT"]
intervalos = {"15m": "15", "1h": "60", "4h": "240"}
ultimos_alertas = {}

def enviar_alerta(mensagem):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem}
            requests.post(url, data=data)
        except:
            print("Erro Telegram")

    if DISCORD_WEBHOOK_URL:
        try:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": mensagem})
        except:
            print("Erro Discord")

def enviar_imagem(img_path):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        files = {'photo': open(img_path, 'rb')}
        data = {"chat_id": TELEGRAM_CHAT_ID}
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        requests.post(url, data=data, files=files)

def calcular_fibonacci(df):
    high = df['high'].max()
    low = df['low'].min()
    diff = high - low
    return {
        '0.236': high - 0.236 * diff,
        '0.382': high - 0.382 * diff,
        '0.5': high - 0.5 * diff,
        '0.618': high - 0.618 * diff,
        '0.786': high - 0.786 * diff,
    }

def plotar_grafico(df, symbol, tf_nome):
    plt.figure(figsize=(10, 4))
    df['close'].plot(label='Preço')
    EMAIndicator(df["close"], window=50).ema_indicator().plot(label='EMA 50')
    EMAIndicator(df["close"], window=200).ema_indicator().plot(label='EMA 200')
    plt.title(f"{symbol} - {tf_nome}")
    plt.legend()
    img_path = f"/tmp/{symbol}_{tf_nome}.png"
    plt.savefig(img_path)
    plt.close()
    return img_path

def alerta_repetido(chave):
    agora = time.time()
    if chave in ultimos_alertas and agora - ultimos_alertas[chave] < 3600:
        return True
    ultimos_alertas[chave] = agora
    return False

def analisar_mercado():
    for simbolo in symbols:
        for tf_nome, tf in intervalos.items():
            try:
                url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={simbolo}&interval={tf}&limit=200"
                r = requests.get(url)
                candles = r.json()["result"]["list"]
                df = pd.DataFrame(candles, columns=[
                    "timestamp", "open", "high", "low", "close", "volume", "_"
                ])
                df = df.astype(float)
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
                df.set_index("timestamp", inplace=True)

                rsi = RSIIndicator(df["close"]).rsi().iloc[-1]
                ema9 = EMAIndicator(df["close"], window=9).ema_indicator().iloc[-1]
                ema21 = EMAIndicator(df["close"], window=21).ema_indicator().iloc[-1]
                ema50 = EMAIndicator(df["close"], window=50).ema_indicator().iloc[-1]
                ema200 = EMAIndicator(df["close"], window=200).ema_indicator().iloc[-1]
                preco_atual = df["close"].iloc[-1]
                fibs = calcular_fibonacci(df)

                mensagem = f"\n📊 *{simbolo}* [{tf_nome}]\n"
                mensagem += f"• 💰 Preço: {preco_atual:.2f}\n"
                mensagem += f"• 📈 RSI: {rsi:.2f}\n"
                if rsi > 70:
                    mensagem += "  ⚠️ RSI acima de 70 (sobrecompra)\n"
                elif rsi < 30:
                    mensagem += "  ⚠️ RSI abaixo de 30 (sobrevenda)\n"

                mensagem += f"• 🟨 EMA 9: {ema9:.2f} | EMA 21: {ema21:.2f}\n"
                mensagem += f"• 🟩 EMA 50: {ema50:.2f} | EMA 200: {ema200:.2f}\n"
                mensagem += f"• 🔢 Fibonacci:\n"
                for nivel, valor in fibs.items():
                    mensagem += f"   - {nivel}: {valor:.2f}\n"

                if ema9 > ema21 and df["close"].iloc[-2] < ema21 and not alerta_repetido(f"{simbolo}_{tf_nome}_cross_up"):
                    mensagem += "• ✅ Cruzamento de alta detectado (EMA 9 > EMA 21)\n"
                if ema9 < ema21 and df["close"].iloc[-2] > ema21 and not alerta_repetido(f"{simbolo}_{tf_nome}_cross_down"):
                    mensagem += "• ⚠️ Cruzamento de baixa detectado (EMA 9 < EMA 21)\n"

                if detectar_oco(df) and not alerta_repetido(f"{simbolo}_{tf_nome}_oco"):
                    mensagem += "• 📉 Padrão OCO detectado!\n"
                if detectar_triangulo(df) and not alerta_repetido(f"{simbolo}_{tf_nome}_triangulo"):
                    mensagem += "• 🔺 Padrão Triângulo detectado!\n"
                if detectar_cunha(df) and not alerta_repetido(f"{simbolo}_{tf_nome}_cunha"):
                    mensagem += "• 🔻 Padrão Cunha detectada!\n"

                enviar_alerta(mensagem)
                imagem = plotar_grafico(df, simbolo, tf_nome)
                enviar_imagem(imagem)

            except Exception as e:
                print(f"Erro em {simbolo}-{tf_nome}: {e}")

@app.route("/")
def status():
    return jsonify({"status": "Bot rodando", "ativos": symbols})

@app.route("/test")
def teste():
    enviar_alerta("🧪 Teste de funcionamento do bot")
    return jsonify({"teste": "ok"})

def keep_alive():
    while True:
        try:
            requests.get(f"{RENDER_EXTERNAL_URL}/")
            print("✅ Keep-alive ping enviado")
        except:
            print("⚠️ Falha no Keep-alive")
        time.sleep(300)

def agendar():
    schedule.every(1).hours.do(analisar_mercado)
    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    print("🚀 Bot com alertas inteligentes iniciado")
    threading.Thread(target=agendar, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)

