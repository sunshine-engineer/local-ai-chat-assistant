"""SQLAlchemy models for chat sessions and messages.

File: postgres/models.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class ChatSession(Base):
    """Map persisted chat-session identifiers, titles and creation timestamps."""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)

    title = Column(String)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Message(Base):
    """Map a persisted role-labelled message to its parent chat session."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)

    session_id = Column(Integer, ForeignKey("sessions.id"))

    role = Column(String)

    message = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
