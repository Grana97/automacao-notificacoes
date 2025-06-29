import time
import requests
import os
from flask import Flask, jsonify
from threading import Thread
import schedule
from datetime import datetime

app = Flask(__name__)

# Status da aplicação
app_status = {
    "iniciado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "ultima_notificacao": "Nenhuma ainda",
    "total_notificacoes": 0,
    "status": "Rodando"
}

# Configurações de criptomoedas
CRYPTO_SYMBOLS = ["bitcoin", "ethereum", "solana", "aave", "ripple"]
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"
VS_CURRENCY = "usd"

# Telegram
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Discord
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

# Cache
last_notification_time = {}
last_hourly_summary_time = None

@app.route('/')
def home():
    html = f"""
    <h1>🤖 Bot de Cripto via CoinGecko</h1>
    <p><strong>Status:</strong> ✅ Ativo</p>
    <p><strong>Iniciado em:</strong> {app_status['iniciado_em']}</p>
    <p><strong>Total enviadas:</strong> {app_status['total_notificacoes']}</p>
    <p><strong>Última:</strong> {app_status['ultima_notificacao']}</p>
    <br>
    <a href="/status">Status JSON</a> | <a href="/test">Testar</a>
    """
    return html

@app.route('/status')
def status():
    return jsonify(app_status)

@app.route('/test')
def test_notification():
    try:
        enviar_notificacao("🧪 Teste de funcionamento do bot de cripto via CoinGecko!")
        return jsonify({"message": "Teste enviado!", "status": "success"})
    except Exception as e:
        return jsonify({"message": f"Erro: {str(e)}", "status": "error"})

def enviar_discord(mensagem):
    if not DISCORD_WEBHOOK:
        return False
    data = {"content": mensagem, "username": "CryptoBot"}
    response = requests.post(DISCORD_WEBHOOK, json=data)
    return response.status_code in [200, 204]

def enviar_telegram(mensagem):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem}
    response = requests.post(url, data=payload)
    return response.status_code == 200

def enviar_notificacao(mensagem):
    sucesso_discord = enviar_discord(mensagem)
    sucesso_telegram = enviar_telegram(mensagem)
    if sucesso_discord or sucesso_telegram:
        app_status["ultima_notificacao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        app_status["total_notificacoes"] += 1
    return sucesso_discord or sucesso_telegram

def get_crypto_data():
    try:
        params = {
            "ids": ",".join(CRYPTO_SYMBOLS),
            "vs_currencies": VS_CURRENCY,
            "include_24hr_change": "true"
        }
        response = requests.get(COINGECKO_API_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Erro ao obter dados do CoinGecko: {e}")
        return {}

def realizar_analise():
    global last_notification_time, last_hourly_summary_time

    agora = datetime.now()
    dados = get_crypto_data()
    if not dados:
        return

    resumo = "📊 **Resumo Cripto (CoinGecko)** 📊\n\n"
    alertas = []

    for simbolo in CRYPTO_SYMBOLS:
        if simbolo not in dados:
            continue
        preco = dados[simbolo][VS_CURRENCY]
        variacao = dados[simbolo].get(f"{VS_CURRENCY}_24h_change", 0)

        status = "🟢" if variacao > 0 else "🔴" if variacao < -2 else "🟡"
        resumo += f"{status} **{simbolo.upper()}**: ${preco:.2f} ({variacao:+.2f}%)\n"

        key = f"{simbolo}_{int(agora.timestamp()) // 600}"
        if abs(variacao) > 5 and key not in last_notification_time:
            direcao = "📈" if variacao > 0 else "📉"
            alertas.append(f"🚨 {simbolo.upper()}: {direcao} {variacao:+.2f}% - ${preco:.2f}")
            last_notification_time[key] = agora

    for alerta in alertas:
        enviar_notificacao(alerta)

    if not last_hourly_summary_time or (agora - last_hourly_summary_time).seconds >= 3600:
        enviar_notificacao(resumo)
        last_hourly_summary_time = agora

def agendar_tarefas():
    schedule.every(1).minutes.do(realizar_analise)
    while True:
        schedule.run_pending()
        time.sleep(30)

def keep_alive():
    url = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:5000")
    while True:
        try:
            requests.get(f"{url}/status", timeout=10)
        except:
            pass
        time.sleep(300)

if __name__ == "__main__":
    enviar_notificacao("🚀 Bot de Cripto via CoinGecko online!")
    Thread(target=agendar_tarefas, daemon=True).start()
    Thread(target=keep_alive, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
