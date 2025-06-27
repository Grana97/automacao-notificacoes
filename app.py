import time
import requests
import os
from flask import Flask, jsonify
from threading import Thread
import schedule
from datetime import datetime

app = Flask(__name__)

# Variável para armazenar status
app_status = {
    "iniciado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "ultima_notificacao": "Nenhuma ainda",
    "total_notificacoes": 0,
    "status": "Rodando"
}

@app.route('/')
def home():
    return """
    <h1>🤖 Automação de Notificações</h1>
    <p><strong>Status:</strong> ✅ Ativo e funcionando!</p>
    <p><strong>Iniciado em:</strong> {}</p>
    <p><strong>Total de notificações enviadas:</strong> {}</p>
    <p><strong>Última notificação:</strong> {}</p>
    <br>
    <a href="/status">Ver Status JSON</a> | 
    <a href="/test">Testar Notificação</a>
    """.format(
        app_status["iniciado_em"],
        app_status["total_notificacoes"], 
        app_status["ultima_notificacao"]
    )

@app.route('/status')
def status():
    return jsonify(app_status)

@app.route('/test')
def test_notification():
    """Endpoint para testar notificação manualmente"""
    try:
        enviar_notificacao_teste()
        return jsonify({"message": "Notificação de teste enviada!", "status": "success"})
    except Exception as e:
        return jsonify({"message": f"Erro: {str(e)}", "status": "error"})

def enviar_notificacao():
    """Função principal de notificação - PERSONALIZE AQUI"""
    try:
        agora = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
        
        # EXEMPLO: Notificação simples no console
        mensagem = f"🔔 Notificação automática enviada às {agora}"
        print(mensagem)
        
        # AQUI VOCÊ PODE ADICIONAR:
        # - Telegram Bot
        # - Discord Webhook
        # - Email
        # - WhatsApp Business API
        # - Qualquer outra integração
        
        # Exemplo de integração com Telegram (descomente e configure):
        # telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        # telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        # if telegram_bot_token and telegram_chat_id:
        #     telegram_url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
        #     telegram_data = {"chat_id": telegram_chat_id, "text": mensagem}
        #     requests.post(telegram_url, data=telegram_data, timeout=10)
        
        # Atualizar status
        app_status["ultima_notificacao"] = agora
        app_status["total_notificacoes"] += 1
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao enviar notificação: {e}")
        return False

def enviar_notificacao_teste():
    """Notificação de teste"""
    agora = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
    print(f"🧪 TESTE: Notificação manual às {agora}")
    app_status["ultima_notificacao"] = f"TESTE - {agora}"
    app_status["total_notificacoes"] += 1

def agendar_tarefas():
    """Configurar agendamentos - PERSONALIZE AQUI"""
    
    # Exemplos de agendamentos (descomente o que quiser usar):
    
    # A cada 30 minutos
    schedule.every(30).minutes.do(enviar_notificacao)
    
    # A cada hora
    # schedule.every().hour.do(enviar_notificacao)
    
    # Diariamente às 9h
    # schedule.every().day.at("09:00").do(enviar_notificacao)
    
    # Segunda, quarta e sexta às 14h
    # schedule.every().monday.at("14:00").do(enviar_notificacao)
    # schedule.every().wednesday.at("14:00").do(enviar_notificacao)
    # schedule.every().friday.at("14:00").do(enviar_notificacao)
    
    print("📅 Agendamentos configurados!")
    print("⏰ Próxima execução:", schedule.next_run())
    
    # Loop principal do agendador
    while True:
        schedule.run_pending()
        time.sleep(60)  # Verifica a cada minuto

def keep_alive():
    """Mantém o app ativo (anti-hibernação)"""
    # Pega a URL do app no Render
    app_url = os.environ.get('RENDER_EXTERNAL_URL')
    if not app_url:
        app_url = "http://localhost:5000"  # Para testes locais
    
    while True:
        try:
            response = requests.get(f"{app_url}/status", timeout=10)
            if response.status_code == 200:
                print("✅ Keep-alive: App está ativo")
            else:
                print(f"⚠️ Keep-alive: Status {response.status_code}")
        except Exception as e:
            print(f"❌ Keep-alive erro: {e}")
        
        time.sleep(300)  # Ping a cada 5 minutos

if __name__ == '__main__':
    print("🚀 Iniciando Automação de Notificações...")
    print("📊 Dashboard disponível em: http://localhost:5000")
    
    # Iniciar agendador em thread separada
    print("📅 Iniciando agendador...")
    scheduler_thread = Thread(target=agendar_tarefas)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    # Iniciar keep-alive em thread separada
    print("💓 Iniciando keep-alive...")
    keepalive_thread = Thread(target=keep_alive)
    keepalive_thread.daemon = True
    keepalive_thread.start()
    
    # Enviar primeira notificação
    print("📱 Enviando primeira notificação...")
    enviar_notificacao()
    
    # Iniciar servidor Flask
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Servidor iniciando na porta {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

