import time
import requests
import os
from flask import Flask, jsonify
from threading import Thread
import schedule
from datetime import datetime
import pandas as pd
import numpy as np

app = Flask(__name__)

# Status da aplicação
app_status = {
    "iniciado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "ultima_notificacao": "Nenhuma ainda",
    "total_notificacoes": 0,
    "status": "Rodando"
}

# Configurações de criptomoedas e análise
CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT", "AAVEUSDT", "XRPUSDT"]
BINANCE_API_URL = "https://api.binance.com/api/v3/klines"
INTERVAL = "1m"

# Cache para evitar spam de notificações
last_notification_time = {}

@app.route('/' )
def home():
    return f"""
    <h1>🤖 Automação de Análise de Cripto - Discord</h1>
    <p><strong>Status:</strong> ✅ Ativo</p>
    <p><strong>Iniciado em:</strong> {app_status['iniciado_em']}</p>
    <p><strong>Total enviadas:</strong> {app_status['total_notificacoes']}</p>
    <p><strong>Última:</strong> {app_status['ultima_notificacao']}</p>
    <br>
    <a href="/status">Status JSON</a> | <a href="/test">Testar Notificação</a>
    """

@app.route('/status')
def status():
    return jsonify(app_status)

@app.route('/test')
def test_notification():
    try:
        enviar_notificacao_teste()
        return jsonify({"message": "Notificação teste enviada para Discord!", "status": "success"})
    except Exception as e:
        return jsonify({"message": f"Erro: {str(e)}", "status": "error"})

def enviar_discord(mensagem):
    """Envia mensagem para o Discord"""
    try:
        webhook_url = os.environ.get('DISCORD_WEBHOOK')
        
        if not webhook_url:
            print("❌ Webhook do Discord não configurado")
            return False
            
        data = {
            "content": mensagem,
            "username": "Crypto Bot Manus"
        }
        
        response = requests.post(webhook_url, json=data, timeout=10)
        
        if response.status_code in [200, 204]:
            print(f"✅ Discord enviado: {mensagem}")
            return True
        else:
            print(f"❌ Erro Discord: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao enviar Discord: {e}")
        return False

def get_klines(symbol, interval, limit=100):
    """Obtém dados de velas da Binance"""
    try:
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        response = requests.get(BINANCE_API_URL, params=params, timeout=10)
        response.raise_for_status()
        klines = response.json()
        
        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'quote_asset_volume', 'number_of_trades', 
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        df['close'] = pd.to_numeric(df['close'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        df['open'] = pd.to_numeric(df['open'])
        return df
    except Exception as e:
        print(f"❌ Erro ao obter dados para {symbol}: {e}")
        return None

def calculate_rsi(df, window=14):
    """Calcula o RSI"""
    try:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not rsi.empty else 50
    except:
        return 50

def calculate_moving_averages(df, short_window=20, long_window=50):
    """Calcula médias móveis"""
    try:
        ma_short = df['close'].rolling(window=short_window).mean().iloc[-1]
        ma_long = df['close'].rolling(window=long_window).mean().iloc[-1]
        return ma_short, ma_long
    except:
        return 0, 0

def calculate_fibonacci_levels(df):
    """Calcula níveis de Fibonacci"""
    try:
        high = df['high'].max()
        low = df['low'].min()
        diff = high - low
        levels = {
            "0%": high,
            "23.6%": high - 0.236 * diff,
            "38.2%": high - 0.382 * diff,
            "50%": high - 0.5 * diff,
            "61.8%": high - 0.618 * diff,
            "100%": low
        }
        return levels
    except:
        return {}

def realizar_analise_completa():
    """Realiza a análise técnica para todas as moedas"""
    global last_notification_time
    
    print(f"📊 Iniciando análise às {datetime.now().strftime('%H:%M:%S')}")
    
    resumo = "📈 **Análise de Criptomoedas** 📈\n\n"
    
    for symbol in CRYPTO_SYMBOLS:
        try:
            df = get_klines(symbol, INTERVAL)
            if df is None:
                continue
                
            current_price = df['close'].iloc[-1]
            
            # RSI
            rsi = calculate_rsi(df)
            rsi_status = ""
            if rsi > 70:
                rsi_status = "🔴 Sobrecomprado"
            elif rsi < 30:
                rsi_status = "🟢 Sobrevendido"
            else:
                rsi_status = "🟡 Neutro"

            # Médias Móveis
            ma_short, ma_long = calculate_moving_averages(df)
            ma_trend = "📈 Alta" if ma_short > ma_long else "📉 Baixa"

            # Alertas importantes
            alerts = []
            if rsi > 75:
                alerts.append("⚠️ RSI muito alto!")
            elif rsi < 25:
                alerts.append("⚠️ RSI muito baixo!")

            # Evitar spam - alertar apenas mudanças significativas
            if alerts:
                key = f"{symbol}_alert"
                if key not in last_notification_time or (datetime.now() - last_notification_time[key]).total_seconds() > 600:
                    alert_msg = f"🚨 **{symbol}** - ${current_price:.4f}\n" + "\n".join(alerts)
                    enviar_discord(alert_msg)
                    last_notification_time[key] = datetime.now()

            resumo += f"**{symbol}:** ${current_price:.4f}\n"
            resumo += f"RSI: {rsi:.1f} {rsi_status} | Trend: {ma_trend}\n\n"

        except Exception as e:
            print(f"❌ Erro ao analisar {symbol}: {e}")
            resumo += f"**{symbol}:** Erro na análise\n\n"

    # Resumo a cada hora
    if datetime.now().minute == 0:
        enviar_discord(resumo)

def enviar_notificacao_teste():
    """Notificação de teste manual"""
    agora = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
    mensagem = f"🧪 **TESTE - Bot de Cripto**\n\n📅 {agora}\n🚀 Sistema funcionando!"
    
    sucesso = enviar_discord(mensagem)
    app_status["ultima_notificacao"] = f"TESTE - {agora}"
    if sucesso:
        app_status["total_notificacoes"] += 1

def agendar_tarefas():
    """Configurar agendamentos"""
    # Análise a cada 2 minutos
    schedule.every(2).minutes.do(realizar_analise_completa)
    
    print("📅 Análise configurada para cada 2 minutos!")
    
    while True:
        schedule.run_pending()
        time.sleep(30)

def keep_alive():
    """Mantém app ativo"""
    app_url = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:5000' )
    
    while True:
        try:
            response = requests.get(f"{app_url}/status", timeout=10)
            if response.status_code == 200:
                print("✅ Keep-alive ativo")
        except:
            print("❌ Keep-alive erro")
        time.sleep(300)

if __name__ == '__main__':
    print("🚀 Iniciando Bot de Análise de Criptomoedas...")
    
    # Mensagem inicial
    enviar_discord("🚀 **Bot de Cripto Iniciado!**\n\n✅ Monitorando: BTC, ETH, SOL, HYPE, AAVE, XRP\n⏰ Análise a cada 2 minutos")
    
    # Threads
    Thread(target=agendar_tarefas, daemon=True).start()
    Thread(target=keep_alive, daemon=True).start()
    
    # Servidor
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

