from typing import Dict, TypedDict, List, Annotated, Literal
import operator
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from app.utils.intent_classifier import classify_intent
from app.config.config import OPENAI_API_KEY
from rich.console import Console
from langsmith import traceable

console = Console()

# Función para fusionar diccionarios
def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    merged = dict1.copy()
    merged.update(dict2)
    return merged

# Función para fusionar listas
def merge_lists(list1: List, list2: List) -> List:
    return list1 + list2

# Definir el estado del grafo
class ConversationState(TypedDict):
    # Usar Annotated con la función merge_dicts para user_info
    user_info: Annotated[Dict, merge_dicts]
    # Usar Annotated con la función merge_lists para messages
    messages: Annotated[List[Dict], merge_lists]
    collected_data: Dict
    intent: str
    current_step: str

llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-3.5-turbo")

prompts = {
    "greeting": ChatPromptTemplate.from_template(
        """Eres un asistente de ventas virtual amigable para una empresa.
        Saluda al cliente de manera cordial, preséntate como asistente virtual y solicita directamente su nombre y correo electrónico.
        
        Hazlo de manera natural y amigable, como si fuera una conversación por WhatsApp. Explica brevemente que necesitas estos datos para brindarle un mejor servicio.
        
        Historial de conversación:
        {conversation_history}
        """
    ),
    "get_name": ChatPromptTemplate.from_template(
        """Eres un asistente de ventas virtual amigable.
        El cliente te ha dicho su nombre: {name}.
        
        Agradécele por compartir su nombre y ahora pregúntale por su correo electrónico.
        
        Hazlo de manera natural y amigable, como si fuera una conversación por WhatsApp.
        
        Historial de conversación:
        {conversation_history}
        """
    ),
    "get_email": ChatPromptTemplate.from_template(
        """Eres un asistente de ventas virtual amigable.
        El cliente te ha dado su correo electrónico: {email}.
        
        Agradécele y ahora pregúntale en qué puedes ayudarle hoy.
        Menciona que puedes ayudar con:
        - Información de horarios
        - Reservaciones
        - Consulta de órdenes
        - Información de productos
        - Quejas o sugerencias
        
        Hazlo de manera natural y amigable, como si fuera una conversación por WhatsApp.
        
        Historial de conversación:
        {conversation_history}
        """
    ),
    "provide_service": ChatPromptTemplate.from_template(
        """Eres un asistente de ventas virtual amigable.
        
        El cliente necesita ayuda con: {intent}
        
        Basándote en el intent del cliente, proporciona una respuesta útil y relevante.
        Si el cliente quiere realizar un nuevo pedido, ayúdale a hacerlo.
        Si necesita información sobre productos, proporciona detalles generales.
        Si tiene una queja, muestra empatía y ofrece soluciones.
        
        Hazlo de manera natural, como si fuera una conversación por WhatsApp.
        
        Historial de conversación:
        {conversation_history}
        
        Información del usuario:
        Nombre: {name}
        Email: {email}
        """
    )
}

def build_conversation_history(state: ConversationState) -> str:
    return "\n".join([f"{m['role']}: {m['content']}" for m in state["messages"]])

def request_missing_data(state: ConversationState, data_type: str) -> Dict:
    conversation_history = build_conversation_history(state)
    prompt_template = ChatPromptTemplate.from_template(
        f"""Eres un asistente de ventas virtual amigable.
        Necesito tu {data_type} para continuar con el servicio.
        
        Por favor, comparte tu {data_type} para poder ayudarte mejor.
        
        Hazlo de manera natural y amigable, como si fuera una conversación por WhatsApp.
        
        Historial de conversación:
        {{conversation_history}}
        """
    )
    response = llm.invoke(prompt_template.format(conversation_history=conversation_history))
    console.log('[red] -> Respuesta del asistente: [/red]', response.content)
    # Devolver solo los cambios, no un estado completo
    return {
        "messages": [{"role": "assistant", "content": response.content}],
        "current_step": "get_name" if data_type == "nombre" else "get_email"
    }

@traceable
def greeting(state: ConversationState) -> Dict:
    console.log('Estado inicial de la conversación:', state)
    conversation_history = build_conversation_history(state)
    response = llm.invoke(prompts["greeting"].format(conversation_history=conversation_history))
    # Retornar solo los cambios al estado
    return {
        "messages": [{"role": "assistant", "content": response.content}],
        "current_step": "validate_user_info"
    }

@traceable
def validate_user_info(state: ConversationState) -> Dict:
    console.log('Entrando en la validacion de user info')
    name = state["user_info"].get("name", "Unknown")
    email = state["user_info"].get("email", "unknown@example.com")
    
    if name == "Unknown":
        console.log('Nombre no encontrado, pidiendo nombre')
        return request_missing_data(state, "nombre")
    
    if email == "unknown@example.com" or not ("@" in email and "." in email):
        console.log('Email no encontrado o inválido, pidiendo email')
        return request_missing_data(state, "correo electrónico")
    
    console.log('Nombre y email válidos, continuando')
    # Si todo está validado, continúa al siguiente paso
    return {
        "current_step": "determine_intent"
    }

@traceable
def get_name(state: ConversationState) -> Dict:
    user_message = state["messages"][-1]["content"]
    extract_prompt = ChatPromptTemplate.from_template(
        """Extrae el nombre del siguiente mensaje:
        
        Mensaje: {message}
        
        Solo devuelve el nombre sin explicaciones ni comillas. Si no hay un nombre claro, devuelve 'Unknown'."""
    )
    name_chain = extract_prompt | llm
    name = name_chain.invoke({"message": user_message}).content.strip()
    
    if name == "Unknown":
        # Volver a pedir nombre
        return request_missing_data(state, "nombre")
    
    conversation_history = build_conversation_history(state)
    response = llm.invoke(prompts["get_name"].format(name=name, conversation_history=conversation_history))
    
    # Retornar solo los cambios
    return {
        "user_info": {"name": name},
        "messages": [{"role": "assistant", "content": response.content}],
        "current_step": "validate_user_info"
    }

@traceable
def get_email(state: ConversationState) -> Dict:
    user_message = state["messages"][-1]["content"]
    extract_prompt = ChatPromptTemplate.from_template(
        """Extrae el email del siguiente mensaje:
        
        Mensaje: {message}
        
        Solo devuelve el email sin explicaciones ni comillas. Si no hay un email claro, devuelve 'unknown@example.com'."""
    )
    email_chain = extract_prompt | llm
    email = email_chain.invoke({"message": user_message}).content.strip()
    
    if email == "unknown@example.com" or not ("@" in email and "." in email):
        return request_missing_data(state, "correo electrónico")
    
    conversation_history = build_conversation_history(state)
    response = llm.invoke(prompts["get_email"].format(email=email, conversation_history=conversation_history))
    
    # Retornar solo los cambios
    return {
        "user_info": {"email": email},
        "messages": [{"role": "assistant", "content": response.content}],
        "current_step": "validate_user_info"
    }

@traceable
def determine_intent(state: ConversationState) -> Dict:
    user_message = state["messages"][-1]["content"]
    intent = classify_intent(user_message)
    return {
        "intent": intent,
        "current_step": "provide_service"
    }

@traceable
def provide_service(state: ConversationState) -> Dict:
    name = state["user_info"].get("name", "Unknown")
    email = state["user_info"].get("email", "unknown@example.com")
    
    conversation_history = build_conversation_history(state)
    
    response = llm.invoke(prompts["provide_service"].format(
        intent=state["intent"],
        name=name,
        email=email,
        conversation_history=conversation_history
    ))
    
    # Retornar solo los cambios
    return {
        "messages": [{"role": "assistant", "content": response.content}],
        "current_step": "determine_intent"  # Para continuar la conversación
    }

@traceable
def should_continue(state: ConversationState) -> Literal["continue_conversation", "end_conversation"]:
    last_user_messages = [m for m in state["messages"] if m["role"] == "user"]
    if not last_user_messages:
        return "continue_conversation"
    last_message = last_user_messages[-1]["content"].lower()
    end_keywords = ["adios", "adiós", "chao", "hasta luego", "terminar", 
                    "finalizar", "gracias por tu ayuda", "gracias por todo", 
                    "eso es todo", "eso sería todo"]
    if any(keyword in last_message for keyword in end_keywords):
        return "end_conversation"
    bot_messages_count = len([m for m in state["messages"] if m["role"] == "assistant"])
    if bot_messages_count > 10:
        return "end_conversation"
    return "continue_conversation"

@traceable
def router(state: ConversationState) -> str:
    return state["current_step"]

@traceable
def create_conversation_graph():
    workflow = StateGraph(ConversationState)
    workflow.add_node("greeting", greeting)
    workflow.add_node("validate_user_info", validate_user_info)

    workflow.add_node("get_name", get_name)
    workflow.add_node("get_email", get_email)
    workflow.add_node("determine_intent", determine_intent)
    workflow.add_node("provide_service", provide_service)
    
    # AQUI SE DEFINE CUAL ES EL NODO INICIAL
    workflow.set_entry_point("greeting")
    # DESPUES DE EJECUTAR GREETING, SE VA A VALIDAR LA INFO DEL USUARIO
    workflow.add_edge("greeting", "validate_user_info")

    # workflow.add_edge("validate_user_info", "get_name")
    # workflow.add_edge("validate_user_info", "get_email")
    # workflow.add_edge("validate_user_info", "determine_intent")
    # workflow.add_edge("get_name", "validate_user_info")
    # workflow.add_edge("get_email", "validate_user_info")
    # workflow.add_edge("determine_intent", "provide_service")
    workflow.add_conditional_edges(
        "provide_service",
        should_continue,
        {
            "continue_conversation": "determine_intent",
            "end_conversation": END,
            "get_name": END,
            "get_email": END,
        }
    )
    return workflow.compile()

conversation_graph = create_conversation_graph()

@traceable
def process_message(message: str, state: ConversationState = None) -> Dict:
    if state is None:
        state = {
            "user_info": {},
            "messages": [],
            "collected_data": {},
            "intent": "",
            "current_step": "greeting"
        }
    
    # Agregar el mensaje del usuario al estado
    if "messages" in state:
        state["messages"].append({"role": "user", "content": message})
    else:
        state["messages"] = [{"role": "user", "content": message}]
    
    result = conversation_graph.invoke(state)
    return {
        "response": result["messages"][-1]["content"],
        "state": result
    }