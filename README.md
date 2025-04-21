# Asistente de Ventas Conversacional

Una aplicación de chat estilo WhatsApp que utiliza LangChain y LangGraph para brindar soporte de ventas automatizado.

## Características

- Interfaz tipo WhatsApp para conversaciones naturales
- Clasificación automática de intenciones del usuario
- Flujo conversacional basado en LangGraph
- Almacenamiento en base de datos MySQL
- Recopilación de información de usuario (nombre y email)
- Detección de intenciones: horarios, reservaciones, pedidos, quejas, etc.

## Requisitos

- Python 3.7+
- MySQL Server
- Cuenta en OpenAI (para la API)

## Instalación

1. Clonar el repositorio
2. Crear un entorno virtual e instalar dependencias:
```
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install flask langchain langchain-openai langgraph pymysql sqlalchemy python-dotenv
```

3. Configurar la base de datos MySQL:
```
mysql -u usuario -p < init_db.sql
```

4. Configurar variables de entorno en el archivo `.env`:
```
DATABASE_URL=mysql+pymysql://usuario:contraseña@localhost/whatsapp_bot
OPENAI_API_KEY=tu-clave-api-de-openai
```

## Ejecución

```
python app.py
```

La aplicación estará disponible en `http://127.0.0.1:5000`

## Estructura del Proyecto

```
├── app.py                     # Archivo principal de la aplicación Flask
├── init_db.sql                # Script para inicializar la base de datos
├── app/
│   ├── config/                # Configuración de la aplicación
│   │   └── config.py          # Carga de variables de entorno
│   ├── controllers/           # Controladores
│   │   └── conversation_controller.py  # Controlador de conversaciones
│   ├── database/              # Gestión de la base de datos
│   │   └── db_handler.py      # Funciones para interactuar con la BD
│   ├── models/                # Modelos de datos
│   │   └── models.py          # Definición de modelos SQLAlchemy
│   ├── static/                # Archivos estáticos
│   │   ├── css/
│   │   │   └── style.css      # Estilos CSS
│   │   └── js/
│   │       └── chat.js        # JavaScript para la interfaz
│   ├── templates/             # Plantillas HTML
│   │   └── index.html         # Página principal
│   └── utils/                 # Utilidades
│       ├── conversation_handler.py  # Gestor de flujo conversacional
│       └── intent_classifier.py     # Clasificador de intenciones
```

## Flujo de Trabajo

1. El usuario escribe un mensaje en la interfaz de chat.
2. El sistema recopila información básica (nombre, email).
3. LangGraph gestiona el flujo de la conversación.
4. El clasificador de intenciones determina qué necesita el usuario.
5. Se proporciona una respuesta relevante según la intención detectada.
6. Toda la conversación se almacena en la base de datos para análisis futuro.