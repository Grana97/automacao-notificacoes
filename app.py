from flask import Flask
import os
from indicadores import analisar_ativos
from padroes import detectar_oco, detectar_triangulo, detectar_cunha
import schedule
import time
import threading
import requests

app = Flask(__name__)

# Webhooks e tokens
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Ativos e timeframes
ATIVOS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AAVEUSDT", "XRPUSDT", "HYPEUSDT", "WIFUSDT", "AEROUSDT"]
TIMEFRAMES = ["15m", "1h", "4h"]

# Funções de envio
def enviar_alerta(mensagem):
    # Discord
    if DISCORD_WEBHOOK:
        try:
            requests.post(DISCORD_WEBHOOK, json={"content": mensagem})
        except Exception as e:
            print("Erro Discord:", e)
    # Telegram
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem}
            resposta = requests.post(url, data=data)
            if resposta.status_code != 200:
                print("Erro Telegram:", resposta.status_code, resposta.text)
        except Exception as e:
            print("Erro Telegram:", e)

# Função principal
def monitorar():
    for ativo in ATIVOS:
        for tf in TIMEFRAMES:
            try:
                analise = analisar_ativos(ativo, tf)
                oco = detectar_oco(analise["df"])  # df retornado agora embutido na análise
                triangulo = detectar_triangulo(analise["df"])
                cunha = detectar_cunha(analise["df"])

                mensagem = (
                    f"📊 Análise {ativo} ({tf})\n"
                    f"Preço atual: {analise['preco']}\n"
                    f"RSI: {analise['rsi']}\n"
                    f"EMA 50: {analise['ema_50']} | EMA 200: {analise['ema_200']}\n"
                    f"Fibonacci: {analise['fibonacci']}\n"
                )

                if analise["alerta"]:
                    mensagem += f"🚨 Alerta: {analise['alerta']}\n"

                if oco:
                    mensagem += "🧠 Padrão OCO detectado\n"
                if triangulo:
                    mensagem += "🔺 Triângulo detectado\n"
                if cunha:
                    mensagem += "📐 Cunha detectada\n"

                if analise["alerta"] or oco or triangulo or cunha:
                    enviar_alerta(mensagem)

            except Exception as e:
                print(f"Erro com {ativo} ({tf}):", e)

# Rota principal
@app.route('/')
def index():
    return "✅ Bot com alertas inteligentes iniciado"

# Rota de teste manual
@app.route('/test-alert')
def testar_alerta():
    mensagem = "🧪 Alerta de teste manual disparado via navegador!"
    enviar_alerta(mensagem)
    return "✅ Alerta enviado com sucesso para Discord e Telegram!"

# Loop de agendamento
def iniciar_agendamento():
    schedule.every(2).minutes.do(monitorar)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=iniciar_agendamento).start()
    app.run(debug=False, host="0.0.0.0", port=10000)
