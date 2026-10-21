from sqlalchemy import select
from postgres.db import SessionLocal, engine
from postgres.models import Base, ChatSession, Message

Base.metadata.create_all(bind=engine)


def create_chat_session():
    with SessionLocal.begin() as db:
        chat = ChatSession(title='New Chat')
        db.add(chat)
        db.flush()
        return chat.id


def save_message(session_id, role, message):
    with SessionLocal.begin() as db:
        db.add(Message(session_id=session_id, role=role, message=message))


def load_messages(session_id):
    with SessionLocal() as db:
        return list(db.scalars(select(Message).where(Message.session_id == session_id)
                               .order_by(Message.created_at, Message.id)))


def get_sessions():
    with SessionLocal() as db:
        return list(db.scalars(select(ChatSession).order_by(ChatSession.created_at.desc())))


def rename_chat_session(session_id, new_title):
    with SessionLocal.begin() as db:
        chat = db.get(ChatSession, session_id)
        if chat:
            chat.title = new_title
        return chat
