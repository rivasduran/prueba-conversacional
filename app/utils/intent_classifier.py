from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from app.config.config import OPENAI_API_KEY

# Intents disponibles
INTENTS = [
    "hours_info",
    "reservation_info",
    "cancel_reservation",
    "quejas",
    "order_status",
    "new_order",
    "order_feedback",
    "product_info",
    "discounts",
    "not_applicable"
]

# Inicializar el modelo de chat
llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-3.5-turbo")

def classify_intent(message):
    """
    Clasifica la intención del usuario basado en el mensaje.
    
    Args:
        message (str): Mensaje del usuario
        
    Returns:
        str: Intent clasificado
    """
    prompt = ChatPromptTemplate.from_template(
        """Clasifica el siguiente mensaje de un cliente en una de estas categorías:
        {intents}
        
        Mensaje del cliente: {message}
        
        Solo devuelve el nombre exacto de la categoría sin explicaciones ni comillas.
        """
    )
    
    chain = prompt | llm
    result = chain.invoke({"intents": ", ".join(INTENTS), "message": message})
    intent = result.content.strip().lower()
    
    # Asegurarse que el intent pertenece a la lista de intents válidos
    if intent not in INTENTS:
        intent = "not_applicable"
        
    return intent