from flask import Flask, render_template, request, jsonify, session
import uuid
from app.controllers.conversation_controller import ConversationController
from app.models.models import init_db

# Inicializar la aplicación Flask
app = Flask(__name__, 
            static_folder='app/static', 
            template_folder='app/templates')
app.secret_key = 'your_secret_key_here'  # Cambiar en producción

# Inicializar el controlador de conversaciones
conversation_controller = ConversationController()

# Inicializar la base de datos
# Reemplazamos @app.before_first_request por un contexto de aplicación
with app.app_context():
    init_db()

@app.route('/')
def index():
    # Generar un ID de sesión único si no existe
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    return render_template('index.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    # Obtener el mensaje del usuario
    message = request.json.get('message', '')
    
    # Obtener el ID de sesión
    session_id = session.get('session_id', str(uuid.uuid4()))
    
    # Procesar el mensaje
    result = conversation_controller.handle_message(session_id, message)
    
    return jsonify(result)

@app.route('/reset_conversation', methods=['POST'])
def reset_conversation():
    # Obtener el ID de sesión
    session_id = session.get('session_id', '')
    
    # Reiniciar la conversación
    conversation_controller.reset_conversation(session_id)
    
    # Generar un nuevo ID de sesión
    session['session_id'] = str(uuid.uuid4())
    
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)