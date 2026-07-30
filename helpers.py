

from postgres.db import SessionLocal
from postgres.models import ChatSession, Message
db = SessionLocal() # initializing database


def create_chat_session():

    chat = ChatSession(
        title="New Chat"
    )

    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat.id


def save_message(session_id, role, message):
    msg = Message(
        session_id=session_id,
        role=role,
        message=message
    )
    db.add(msg)
    db.commit()
    

def load_messages(session_id):

    return (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at)
        .all()
    )
    

def get_sessions():

    return (
        db.query(ChatSession)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    
    
    
def rename_chat_session(session_id, new_title):
    chat = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id)
        .first()
    )

    if chat:
        chat.title = new_title
        db.commit()

    return chat

