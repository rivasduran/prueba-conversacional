from app.models.models import Session, User, Conversation

def save_user(name, email):
    """
    Guarda un usuario en la base de datos
    
    Args:
        name (str): Nombre del usuario
        email (str): Email del usuario
        
    Returns:
        int: ID del usuario
    """
    session = Session()
    try:
        # Verificar si el usuario ya existe por email
        existing_user = session.query(User).filter_by(email=email).first()
        if existing_user:
            return existing_user.id
            
        # Si no existe, crear nuevo usuario
        user = User(name=name, email=email)
        session.add(user)
        session.commit()
        return user.id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def save_conversation(user_id, message, response, intent):
    """
    Guarda una conversación en la base de datos
    
    Args:
        user_id (int): ID del usuario
        message (str): Mensaje del usuario
        response (str): Respuesta del asistente
        intent (str): Intención detectada
    """
    session = Session()
    try:
        conversation = Conversation(
            user_id=user_id,
            message=message,
            response=response,
            intent=intent
        )
        session.add(conversation)
        session.commit()
        return conversation.id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_user_by_email(email):
    """
    Obtiene un usuario por su email
    
    Args:
        email (str): Email del usuario
        
    Returns:
        User: Usuario encontrado o None
    """
    session = Session()
    try:
        return session.query(User).filter_by(email=email).first()
    finally:
        session.close()

def get_conversations_by_user_id(user_id):
    """
    Obtiene todas las conversaciones de un usuario
    
    Args:
        user_id (int): ID del usuario
        
    Returns:
        List[Conversation]: Lista de conversaciones
    """
    session = Session()
    try:
        return session.query(Conversation).filter_by(user_id=user_id).all()
    finally:
        session.close()