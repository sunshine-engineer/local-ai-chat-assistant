"""Transactional chat-history persistence helpers.

File: helpers.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

from sqlalchemy import select

from postgres.db import SessionLocal, engine
from postgres.models import Base, ChatSession, Message

Base.metadata.create_all(bind=engine)


def create_chat_session():
    """Create a persisted chat session with the default title.

    Returns:
        Newly persisted session identifier.
    """
    with SessionLocal.begin() as db:
        chat = ChatSession(title="New Chat")
        db.add(chat)
        db.flush()
        return chat.id


def save_message(session_id, role, message):
    """Persist one message in the selected chat session.

    Args:
        session_id: Persisted chat-session identifier.
        role: Message role, normally user or assistant.
        message: Message text to persist.
    """
    with SessionLocal.begin() as db:
        db.add(Message(session_id=session_id, role=role, message=message))


def load_messages(session_id):
    """Load a session's messages in stable chronological order.

    Args:
        session_id: Persisted chat-session identifier.

    Returns:
        Chronologically ordered persisted Message objects.
    """
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(Message)
                .where(Message.session_id == session_id)
                .order_by(Message.created_at, Message.id)
            )
        )


def get_sessions():
    """List chat sessions from newest to oldest.

    Returns:
        ChatSession objects ordered from newest to oldest.
    """
    with SessionLocal() as db:
        return list(db.scalars(select(ChatSession).order_by(ChatSession.created_at.desc())))


def rename_chat_session(session_id, new_title):
    """Rename an existing session without creating a missing one.

    Args:
        session_id: Persisted chat-session identifier.
        new_title: Replacement title for an existing session.

    Returns:
        Updated ChatSession, or None when its identifier is unknown.
    """
    with SessionLocal.begin() as db:
        chat = db.get(ChatSession, session_id)
        if chat:
            chat.title = new_title
        return chat
