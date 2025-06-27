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
CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT", "AAVEUSDT", "XRPUSDT"]
BINANCE_API_URL = "https://api.binance.com/api/v3/ticker/24hr"

# Cache para evitar spam
last_notification_time = {}

@app.route('/' )
def home():
    return f"""
    <h1>🤖 Bot de Análise de Cripto</h1>
    <p><strong>Status:</strong> ✅ Ativo</p>
    <p><strong>Iniciado em:</strong> {app_status['iniciado_em']}</p>
    <p><strong>Total enviadas:</strong> {app_status['total_notificacoes']}</p>
    <p><strong>Última:</strong> {app_status['ultima_notificacao']}</p>
    <br>
    <a href="/status">Status JSON</a> | <a href="/test">Testar</a>
    """

@app.route('/status')
def status():
    return jsonify(app_status)

@app.route('/test')
def test_notification():
    try:
        enviar_notificacao_teste()
        return jsonify({"message": "Teste enviado!", "status": "success"})
    except Exception as e:
        return jsonify({"message": f"Erro: {str(e)}", "status": "error"})

def enviar_discord(mensagem):
    """Envia mensagem para o Discord"""
    try:
        webhook_url = os.environ.get('DISCORD_WEBHOOK')
        
        if not webhook_url:
            print("❌ Webhook não configurado")
            return False
            
        data = {
            "content": mensagem,
            "username": "Crypto Bot"
        }
        
        response = requests.post(webhook_url, json=data, timeout=10)
        
        if response.status_code in [200, 204]:
            print(f"✅ Discord enviado")
            return True
        else:
            print(f"❌ Erro Discord: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def get_crypto_data():
    """Obtém dados das criptomoedas"""
    try:
        response = requests.get(BINANCE_API_URL, timeout=10)
        response.raise_for_status()
        all_data = response.json()
        
        # Filtrar apenas nossas moedas
        crypto_data = {}
        for data in all_data:
            if data['symbol'] in CRYPTO_SYMBOLS:
                crypto_data[data['symbol']] = {
                    'price': float(data['lastPrice']),
                    'change_24h': float(data['priceChangePercent']),
                    'volume': float(data['volume'])
                }
        
        return crypto_data
    except Exception as e:
        print(f"❌ Erro ao obter dados: {e}")
        return {}

def calcular_rsi_simples(prices):
    """RSI simplificado sem pandas"""
    if len(prices) < 14:
        return 50
    
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    avg_gain = sum(gains[-14:]) / 14
    avg_loss = sum(losses[-14:]) / 14
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def realizar_analise():
    """Análise simplificada das criptomoedas"""
    global last_notification_time
    
    print(f"📊 Análise às {datetime.now().strftime('%H:%M:%S')}")
    
    crypto_data = get_crypto_data()
    if not crypto_data:
        return
    
    resumo = "📈 **Análise de Criptomoedas** 📈\n\n"
    alerts = []
    
    for symbol, data in crypto_data.items():
        price = data['price']
        change_24h = data['change_24h']
        
        # Alertas para mudanças significativas
        if abs(change_24h) > 5:  # Mudança > 5%
            direction = "📈" if change_24h > 0 else "📉"
            alerts.append(f"🚨 **{symbol}**: {direction} {change_24h:+.2f}% - ${price:.4f}")
        
        # Status da moeda
        status = "🟢" if change_24h > 0 else "🔴" if change_24h < -2 else "🟡"
        resumo += f"{status} **{symbol}**: ${price:.4f} ({change_24h:+.2f}%)\n"
    
    # Enviar alertas imediatos
    for alert in alerts:
        key = f"alert_{datetime.now().strftime('%H')}"  # Um alerta por hora
        if key not in last_notification_time:
            enviar_discord(alert)
            last_notification_time[key] = datetime.now()
    
    # Resumo a cada hora
    if datetime.now().minute == 0:
        enviar_discord(resumo)

def enviar_notificacao_teste():
    """Teste manual"""
    agora = datetime.now().strftime("%H:%M:%S")
    mensagem = f"🧪 **TESTE**\n\n📅 {agora}\n🚀 Bot funcionando!"
    
    sucesso = enviar_discord(mensagem)
    app_status["ultima_notificacao"] = f"TESTE - {agora}"
    if sucesso:
        app_status["total_notificacoes"] += 1

def agendar_tarefas():
    """Agendamentos"""
    # Análise a cada 2 minutos
    schedule.every(2).minutes.do(realizar_analise)
    
    print("📅 Análise a cada 2 minutos configurada!")
    
    while True:
        schedule.run_pending()
        time.sleep(30)

def keep_alive():
    """Keep alive"""
    app_url = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:5000' )
    
    while True:
        try:
            response = requests.get(f"{app_url}/status", timeout=10)
            if response.status_code == 200:
                print("✅ Keep-alive")
        except:
            print("❌ Keep-alive erro")
        time.sleep(300)

if __name__ == '__main__':
    print("🚀 Iniciando Bot de Cripto...")
    
    # Mensagem inicial
    enviar_discord("🚀 **Bot de Cripto Online!**\n\n✅ Monitorando: BTC, ETH, SOL, HYPE, AAVE, XRP\n⏰ Análise a cada 2 minutos")
    
    # Threads
    Thread(target=agendar_tarefas, daemon=True).start()
    Thread(target=keep_alive, daemon=True).start()
    
    # Servidor
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
