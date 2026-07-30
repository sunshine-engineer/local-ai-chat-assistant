from sqlalchemy.orm import declarative_base
from sqlalchemy import Column,Integer,String,Text,ForeignKey,DateTime
from sqlalchemy.sql import func

Base = declarative_base()

class ChatSession(Base):

    __tablename__="sessions"

    id=Column(Integer,primary_key=True)

    title=Column(String)

    created_at=Column(DateTime(timezone=True),server_default=func.now())


class Message(Base):

    __tablename__="messages"

    id=Column(Integer,primary_key=True)

    session_id=Column(Integer,ForeignKey("sessions.id"))

    role=Column(String)

    message=Column(Text)

    created_at=Column(DateTime(timezone=True),server_default=func.now())