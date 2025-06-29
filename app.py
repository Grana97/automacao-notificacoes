from flask import Flask
import os
import schedule
import time
import threading
import requests
from indicadores import analisar_ativos
from padroes import detectar_oco, detectar_triangulo, detectar_cunha

app = Flask(__name__)

# Variáveis de ambiente
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Lista de ativos e timeframes
ATIVOS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AAVEUSDT", "XRPUSDT", "HYPEUSDT", "WIFUSDT", "AEROUSDT"]
TIMEFRAMES = ["15m", "1h", "4h"]

# Enviar mensagem para Discord e Telegram
def enviar_alerta(mensagem):
    # Discord
    if DISCORD_WEBHOOK:
        try:
            requests.post(DISCORD_WEBHOOK, json={"content": mensagem})
        except Exception as e:
            print("❌ Erro ao enviar para Discord:", e)
    # Telegram
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem}
            resposta = requests.post(url, data=data)
            if resposta.status_code != 200:
                print("❌ Erro Telegram:", resposta.status_code, resposta.text)
        except Exception as e:
            print("❌ Erro ao enviar para Telegram:", e)

# Análise e envio de alertas
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

                if analise.get("alerta"):
                    mensagem += f"🚨 Alerta: {analise['alerta']}\n"
                if oco:
                    mensagem += "🧠 Padrão OCO detectado\n"
                if triangulo:
                    mensagem += "🔺 Triângulo detectado\n"
                if cunha:
                    mensagem += "📐 Cunha detectada\n"

                enviar_alerta(mensagem)

            except Exception as e:
                print(f"❌ Erro ao analisar {ativo} ({tf}):", e)

# Página principal
@app.route('/')
def index():
    return "✅ Bot com alertas inteligentes está rodando"

# Rota de teste
@app.route('/test-alert')
def testar_alerta():
    enviar_alerta("🧪 Alerta de teste manual enviado via navegador!")
    return "✅ Alerta enviado com sucesso!"

# Loop de agendamento
def iniciar_agendamento():
    schedule.every(2).minutes.do(monitorar)
    while True:
        schedule.run_pending()
        time.sleep(1)

# Executar
if __name__ == "__main__":
    threading.Thread(target=iniciar_agendamento).start()
    app.run(debug=False, host="0.0.0.0", port=10000)
