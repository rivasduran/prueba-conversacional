from app.utils.conversation_handler import process_message
from app.database.db_handler import save_user, save_conversation
from typing import Dict, Any

class ConversationController:
    def __init__(self):
        """Inicializa el controlador de conversaciones"""
        self.active_conversations = {}  # Almacena las conversaciones activas por session_id
    
    def handle_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Maneja un mensaje del usuario
        
        Args:
            session_id (str): Identificador único de la sesión
            message (str): Mensaje del usuario
            
        Returns:
            Dict: Diccionario con la respuesta
        """
        # Obtener el estado actual de la conversación si existe
        current_state = self.active_conversations.get(session_id)
        
        # Procesar el mensaje
        result = process_message(message, current_state)
        
        # Actualizar el estado
        new_state = result["state"]
        self.active_conversations[session_id] = new_state
        
        # Guardar en la base de datos si tenemos suficiente información
        if "name" in new_state["user_info"] and "email" in new_state["user_info"]:
            # Guardar o actualizar usuario
            user_id = save_user(
                name=new_state["user_info"]["name"],
                email=new_state["user_info"]["email"]
            )
            
            # Guardar la conversación
            save_conversation(
                user_id=user_id,
                message=message,
                response=result["response"],
                intent=new_state.get("intent", "not_classified")
            )
        
        return {
            "response": result["response"],
            "session_id": session_id,
            "user_info": new_state["user_info"],
            "intent": new_state.get("intent", "")
        }
    
    def reset_conversation(self, session_id: str) -> None:
        """
        Reinicia una conversación
        
        Args:
            session_id (str): Identificador único de la sesión
        """
        if session_id in self.active_conversations:
            del self.active_conversations[session_id]