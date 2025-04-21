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
# Definir el estado del grafo
class ConversationState(TypedDict):
    user_info: Dict
    messages: List[Dict]
    collected_data: Dict
    intent: str
    current_step: str

# LLM para procesamiento conversacional
llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-3.5-turbo")

# Prompts para cada estado del sistema
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

@traceable
def greeting(state: ConversationState) -> ConversationState:
    """Estado inicial de saludo"""
    console.log('Mira el estado de la conversación:', state)
    conversation_history = "\n".join([f"{m['role']}: {m['content']}" for m in state["messages"]])
    console.log('[red] Y esta es el historia:  [/red]')
    console.log(conversation_history)
    response = llm.invoke(prompts["greeting"].format(conversation_history=conversation_history))
    
    new_state = state.copy()
    new_state["messages"].append({"role": "assistant", "content": response.content})
    new_state["current_step"] = "get_name"
    return new_state

@traceable
def get_name(state: ConversationState) -> ConversationState:
    """Recoger el nombre del usuario"""
    # Extrae el nombre del último mensaje
    user_message = state["messages"][-1]["content"]
    
    # Prompt para extraer el nombre
    extract_prompt = ChatPromptTemplate.from_template(
        """Extrae el nombre del siguiente mensaje:
        
        Mensaje: {message}
        
        Solo devuelve el nombre sin explicaciones ni comillas. Si no hay un nombre claro, devuelve 'Unknown'."""
    )
    name_chain = extract_prompt | llm
    name = name_chain.invoke({"message": user_message}).content.strip()
    
    # Verificar si se obtuvo un nombre válido
    if name == "Unknown":
        # Si no hay un nombre válido, volver a preguntar
        conversation_history = "\n".join([f"{m['role']}: {m['content']}" for m in state["messages"]])
        response = llm.invoke(
            ChatPromptTemplate.from_template(
                """Eres un asistente de ventas virtual amigable.
                No has podido identificar un nombre en el mensaje del cliente.
                
                Solicita de nuevo y de manera amable que te proporcione su nombre para poder continuar.
                Explica que necesitas su nombre para poder brindarle un mejor servicio.
                
                Hazlo de manera natural y amigable, como si fuera una conversación por WhatsApp.
                
                Historial de conversación:
                {conversation_history}
                """
            ).format(conversation_history=conversation_history)
        )
        
        new_state = state.copy()
        new_state["messages"].append({"role": "assistant", "content": response.content})
        # Mantener el mismo paso para que vuelva a intentar obtener el nombre
        new_state["current_step"] = "get_name"
        return new_state
    
    conversation_history = "\n".join([f"{m['role']}: {m['content']}" for m in state["messages"]])
    response = llm.invoke(prompts["get_name"].format(
        name=name,
        conversation_history=conversation_history
    ))
    
    new_state = state.copy()
    new_state["user_info"]["name"] = name
    new_state["messages"].append({"role": "assistant", "content": response.content})
    new_state["current_step"] = "get_email"
    return new_state

@traceable
def get_email(state: ConversationState) -> ConversationState:
    """Recoger el email del usuario"""
    # Extrae el email del último mensaje
    user_message = state["messages"][-1]["content"]
    
    # Prompt para extraer el email
    extract_prompt = ChatPromptTemplate.from_template(
        """Extrae el email del siguiente mensaje:
        
        Mensaje: {message}
        
        Solo devuelve el email sin explicaciones ni comillas. Si no hay un email claro, devuelve 'unknown@example.com'."""
    )
    email_chain = extract_prompt | llm
    email = email_chain.invoke({"message": user_message}).content.strip()
    
    # Verificar si se obtuvo un email válido
    if email == "unknown@example.com" or not ("@" in email and "." in email):
        # Si no hay un email válido, volver a preguntar
        conversation_history = "\n".join([f"{m['role']}: {m['content']}" for m in state["messages"]])
        response = llm.invoke(
            ChatPromptTemplate.from_template(
                """Eres un asistente de ventas virtual amigable.
                No has podido identificar un correo electrónico válido en el mensaje del cliente.
                
                Solicita de nuevo y de manera amable que te proporcione su correo electrónico para poder continuar.
                Explica que necesitas su correo electrónico para poder enviarle información y darle seguimiento a sus solicitudes.
                
                Hazlo de manera natural y amigable, como si fuera una conversación por WhatsApp.
                
                Historial de conversación:
                {conversation_history}
                """
            ).format(conversation_history=conversation_history)
        )
        
        new_state = state.copy()
        new_state["messages"].append({"role": "assistant", "content": response.content})
        # Mantener el mismo paso para que vuelva a intentar obtener el email
        new_state["current_step"] = "get_email"
        return new_state
    
    conversation_history = "\n".join([f"{m['role']}: {m['content']}" for m in state["messages"]])
    response = llm.invoke(prompts["get_email"].format(
        email=email,
        conversation_history=conversation_history
    ))
    
    new_state = state.copy()
    new_state["user_info"]["email"] = email
    new_state["messages"].append({"role": "assistant", "content": response.content})
    new_state["current_step"] = "provide_service"
    return new_state

@traceable
def determine_intent(state: ConversationState) -> ConversationState:
    """Determina la intención del usuario"""
    # Verificar si tenemos la información del usuario completa
    name = state["user_info"].get("name", "Unknown")
    email = state["user_info"].get("email", "unknown@example.com")
    
    # Si falta información del usuario, volver al paso correspondiente
    if name == "Unknown":
        # Volver a solicitar el nombre
        new_state = state.copy()
        conversation_history = "\n".join([f"{m['role']}: {m['content']}" for m in state["messages"]])
        response = llm.invoke(
            ChatPromptTemplate.from_template(
                """Eres un asistente de ventas virtual amigable.
                Necesito tu nombre para continuar con el servicio.
                
                Por favor, comparte tu nombre para poder ayudarte mejor.
                
                Hazlo de manera natural y amigable, como si fuera una conversación por WhatsApp.
                
                Historial de conversación:
                {conversation_history}
                """
            ).format(conversation_history=conversation_history)
        )
        new_state["messages"].append({"role": "assistant", "content": response.content})
        new_state["current_step"] = "get_name"
        return new_state
    
    if email == "unknown@example.com" or not ("@" in email and "." in email):
        # Volver a solicitar el email
        new_state = state.copy()
        conversation_history = "\n".join([f"{m['role']}: {m['content']}" for m in state["messages"]])
        response = llm.invoke(
            ChatPromptTemplate.from_template(
                """Eres un asistente de ventas virtual amigable.
                Necesito tu correo electrónico para continuar con el servicio.
                
                Por favor, comparte tu correo electrónico para poder contactarte en caso necesario.
                
                Hazlo de manera natural y amigable, como si fuera una conversación por WhatsApp.
                
                Historial de conversación:
                {conversation_history}
                """
            ).format(conversation_history=conversation_history)
        )
        new_state["messages"].append({"role": "assistant", "content": response.content})
        new_state["current_step"] = "get_email"
        return new_state
    
    # Si tenemos toda la información, proceder con la clasificación de intent
    user_message = state["messages"][-1]["content"]
    intent = classify_intent(user_message)
    
    new_state = state.copy()
    new_state["intent"] = intent
    return new_state

@traceable
def provide_service(state: ConversationState) -> ConversationState:
    """Proporcionar el servicio basado en la intención"""
    # Verificar si tenemos la información del usuario completa
    name = state["user_info"].get("name", "Unknown")
    email = state["user_info"].get("email", "unknown@example.com")
    
    # Validar la información del usuario antes de proporcionar el servicio
    if name == "Unknown" or email == "unknown@example.com" or not ("@" in email and "." in email):
        # Redirigir al flujo adecuado si falta información
        if name == "Unknown":
            new_state = state.copy()
            new_state["current_step"] = "get_name"
            conversation_history = "\n".join([f"{m['role']}: {m['content']}" for m in state["messages"]])
            response = llm.invoke(
                ChatPromptTemplate.from_template(
                    """Eres un asistente de ventas virtual amigable.
                    Para poder ayudarte necesito saber tu nombre.
                    
                    Por favor, comparte tu nombre para poder brindar un servicio personalizado.
                    
                    Hazlo de manera natural y amigable, como si fuera una conversación por WhatsApp.
                    
                    Historial de conversación:
                    {conversation_history}
                    """
                ).format(conversation_history=conversation_history)
            )
            new_state["messages"].append({"role": "assistant", "content": response.content})
            return new_state
        else:
            new_state = state.copy()
            new_state["current_step"] = "get_email"
            conversation_history = "\n".join([f"{m['role']}: {m['content']}" for m in state["messages"]])
            response = llm.invoke(
                ChatPromptTemplate.from_template(
                    """Eres un asistente de ventas virtual amigable.
                    Para poder ayudarte necesito tu correo electrónico.
                    
                    Por favor, comparte un correo electrónico válido para poder enviarte confirmaciones y seguimiento.
                    
                    Hazlo de manera natural y amigable, como si fuera una conversación por WhatsApp.
                    
                    Historial de conversación:
                    {conversation_history}
                    """
                ).format(conversation_history=conversation_history)
            )
            new_state["messages"].append({"role": "assistant", "content": response.content})
            return new_state
    
    conversation_history = "\n".join([f"{m['role']}: {m['content']}" for m in state["messages"]])
    
    # Determinar la intención si aún no se ha hecho
    if not state["intent"]:
        state = determine_intent(state)
    
    response = llm.invoke(prompts["provide_service"].format(
        intent=state["intent"],
        name=name, # Usamos el nombre validado
        email=email, # Usamos el email validado
        conversation_history=conversation_history
    ))
    
    new_state = state.copy()
    new_state["messages"].append({"role": "assistant", "content": response.content})
    return new_state

@traceable
def should_continue(state: ConversationState) -> Literal["continue_conversation", "end_conversation"]:
    """Determina si continuar la conversación o terminarla"""
    # Verificar la conversación por señales de término
    last_user_messages = [m for m in state["messages"] if m["role"] == "user"]
    
    # Si no hay mensajes del usuario, continuamos la conversación
    if not last_user_messages:
        return "continue_conversation"
    
    # Tomar el último mensaje del usuario
    last_message = last_user_messages[-1]["content"].lower()
    
    # Palabras clave que indican que el usuario quiere terminar
    end_keywords = ["adios", "adiós", "chao", "hasta luego", "terminar", 
                    "finalizar", "gracias por tu ayuda", "gracias por todo", 
                    "eso es todo", "eso sería todo"]
    
    # Verificar si alguna palabra clave está en el último mensaje
    if any(keyword in last_message for keyword in end_keywords):
        return "end_conversation"
    
    # Contar cuántos ciclos entre provide_service y determine_intent han ocurrido
    # Podemos estimar esto contando cuántas veces el bot ha respondido
    bot_messages_count = len([m for m in state["messages"] if m["role"] == "assistant"])
    
    # Si hemos tenido muchos intercambios (por ejemplo, más de 10), terminamos la conversación
    # para evitar bucles infinitos
    if bot_messages_count > 10:
        return "end_conversation"
    
    return "continue_conversation"

@traceable
def router(state: ConversationState) -> str:
    """Enruta el flujo de la conversación según el estado actual"""
    return state["current_step"]

# Crear el grafo de conversación
@traceable
def create_conversation_graph():
    # Crear el grafo (sin el parámetro recursion_limit que no es soportado en esta versión)
    workflow = StateGraph(ConversationState)
    
    # Añadir nodos
    workflow.add_node("greeting", greeting)
    workflow.add_node("get_name", get_name)
    workflow.add_node("get_email", get_email)
    workflow.add_node("provide_service", provide_service)
    workflow.add_node("determine_intent", determine_intent)
    
    # Definir el flujo
    workflow.set_entry_point("greeting")
    workflow.add_edge("greeting", "get_name")
    workflow.add_edge("get_name", "get_email")
    workflow.add_edge("get_email", "determine_intent")
    workflow.add_edge("determine_intent", "provide_service")
    
    # Después de proporcionar servicio, decidir si continuar o terminar
    workflow.add_conditional_edges(
        "provide_service",
        should_continue,
        {
            "continue_conversation": "determine_intent",
            "end_conversation": END
        }
    )
    
    return workflow.compile()

# Inicializar el grafo de conversación
conversation_graph = create_conversation_graph()

@traceable
def process_message(message: str, state: ConversationState = None) -> Dict:
    """
    Procesa un mensaje del usuario y devuelve la respuesta y el nuevo estado
    
    Args:
        message: El mensaje del usuario
        state: El estado actual de la conversación (opcional)
        
    Returns:
        Dict con la respuesta y el nuevo estado
    """
    if state is None:
        state = {
            "user_info": {},
            "messages": [],
            "collected_data": {},
            "intent": "",
            "current_step": "greeting"
        }
    
    # Añadir el mensaje del usuario al estado
    state["messages"].append({"role": "user", "content": message})
    
    # Ejecutar el grafo
    result = conversation_graph.invoke(state)
    
    return {
        "response": result["messages"][-1]["content"],
        "state": result
    }