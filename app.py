import time
import requests
import os
from flask import Flask, jsonify
from threading import Thread
import schedule
from datetime import datetime

app = Flask(__name__ )

# Status da aplicação
app_status = {
    "iniciado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "ultima_notificacao": "Nenhuma ainda",
    "total_notificacoes": 0,
    "status": "Rodando"
}

@app.route('/')
def home():
    return f"""
    <h1>🤖 Automação de Notificações - Discord</h1>
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
            "username": "Automação Bot"
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

def enviar_notificacao():
    """Notificação automática principal"""
    try:
        agora = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
        mensagem = f"🔔 **Notificação Automática**\n\n📅 {agora}\n✅ Sistema funcionando perfeitamente!"
        
        # Enviar para Discord
        sucesso = enviar_discord(mensagem)
        
        # Atualizar status
        app_status["ultima_notificacao"] = agora
        if sucesso:
            app_status["total_notificacoes"] += 1
            
        print(f"📱 Notificação processada às {agora}")
        return sucesso
        
    except Exception as e:
        print(f"❌ Erro na notificação: {e}")
        return False

def enviar_notificacao_teste():
    """Notificação de teste manual"""
    agora = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
    mensagem = f"🧪 **TESTE - Notificação Manual**\n\n📅 {agora}\n🚀 Enviado via dashboard!"
    
    sucesso = enviar_discord(mensagem)
    app_status["ultima_notificacao"] = f"TESTE - {agora}"
    if sucesso:
        app_status["total_notificacoes"] += 1

def agendar_tarefas():
    """Configurar agendamentos"""
    # Notificação a cada 30 minutos
    schedule.every(30).minutes.do(enviar_notificacao)
    
    print("📅 Agendamentos configurados!")
    print("⏰ Próxima execução:", schedule.next_run())
    
    while True:
        schedule.run_pending()
        time.sleep(60)

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
    print("🚀 Iniciando Automação com Discord...")
    
    # Testar Discord na inicialização
    enviar_discord("🚀 **Automação Iniciada!**\n\n✅ Sistema online e funcionando 24/7")
    
    # Threads
    Thread(target=agendar_tarefas, daemon=True).start()
    Thread(target=keep_alive, daemon=True).start()
    
    # Servidor
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

