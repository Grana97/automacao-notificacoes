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

# Função para enviar alerta para Telegram e Discord
def enviar_alerta(mensagem):
    # Discord
    if DISCORD_WEBHOOK:
        try:
            requests.post(DISCORD_WEBHOOK, json={"content": mensagem})
        except Exception as e:
            print("Erro ao enviar para Discord:", e)

    # Telegram
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem}
            requests.post(url, data=data)
        except Exception as e:
            print("Erro ao enviar para Telegram:", e)

# Função principal de monitoramento
def monitorar():
    for ativo in ATIVOS:
        for tf in TIMEFRAMES:
            try:
                analise = analisar_ativos(ativo, tf)
                oco = detectar_oco(ativo, tf)
                triangulo = detectar_triangulo(ativo, tf)
                cunha = detectar_cunha(ativo, tf)

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

                enviar_alerta(mensagem)

            except Exception as e:
                print(f"Erro ao analisar {ativo} ({tf}):", e)

# Página principal
@app.route('/')
def index():
    return "✅ Bot com alertas inteligentes iniciado com sucesso!"

# Rota de teste de alerta
@app.route('/test-alert')
def test_alert():
    mensagem = "🧪 Alerta de teste manual disparado com sucesso!"
    enviar_alerta(mensagem)
    return "✅ Alerta de teste enviado com sucesso para Discord e Telegram!"

# Função para agendar a execução contínua
def iniciar_agendamento():
    schedule.every(15).minutes.do(monitorar)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=iniciar_agendamento).start()
    app.run(debug=False, host="0.0.0.0", port=10000)
