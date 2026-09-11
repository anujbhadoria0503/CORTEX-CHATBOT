from typing import List
from datetime import datetime
import uuid
from pydantic import BaseModel
from sqlalchemy import (
    Column,
    Integer,
    Text,
    String,
    DateTime,
    ForeignKey
)
from sqlalchemy.orm import (
    declarative_base,
    relationship
)
Base = declarative_base()
# PYDANTIC MODELS
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    # Optional PDF filename
    filename: str | None = None
class RetrievedChunk(BaseModel):
    id: str
    score: float
    text: str
    filename: str
    # Metadata from document parser
    type: str | None = None
    page: int | None = None
    last_page: int | None = None
    heading: str | None = None
class ChatResponse(BaseModel):
    response: str
    session_id: str
    retrieved_chunks: List[RetrievedChunk]
# CONVERSATION TABLE
class Conversation(Base):
    __tablename__ = "conversations"
    session_id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    title = Column(
        Text,
        default="New Chat"
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow
    )
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )
# MESSAGE TABLE
class Message(Base):
    __tablename__ = "messages"
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    session_id = Column(
        String(36),
        ForeignKey(
            "conversations.session_id"
        ),
        nullable=False
    )
    role = Column(
        Text,
        nullable=False
    )
    content = Column(
        Text,
        nullable=False
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
    conversation = relationship(
        "Conversation",
        back_populates="messages"
    )
# DOCUMENT TABLE
class Document(Base):
    __tablename__ = "documents"
    id = Column(
        String(36),
        primary_key=True
    )
    filename = Column(
        Text
    )
    chunk = Column(
        Text
    )