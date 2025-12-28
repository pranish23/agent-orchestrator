"""
SQLAlchemy models for the orchestrator
"""
from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.database import Base
from app.config import settings

# Get dimensions based on provider
EMBEDDING_DIM = 1536 if settings.llm_provider.lower() == "openai" else 768


class User(Base):
    """User model with OAuth tokens"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    google_access_token = Column(Text, nullable=True)
    google_refresh_token = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    gmail_cache = relationship("GmailCache", back_populates="user", cascade="all, delete-orphan")
    gcal_cache = relationship("GCalCache", back_populates="user", cascade="all, delete-orphan")
    gdrive_cache = relationship("GDriveCache", back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    """Conversation history for context tracking"""
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    query = Column(Text, nullable=False)
    intent = Column(JSONB, nullable=True)
    response = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="conversations")


class GmailCache(Base):
    """Cached Gmail emails with embeddings"""
    __tablename__ = "gmail_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    email_id = Column(String(255), nullable=False)
    thread_id = Column(String(255), nullable=True)
    subject = Column(Text, nullable=True)
    sender = Column(String(255), nullable=True, index=True)
    recipients = Column(JSONB, nullable=True)
    body_preview = Column(Text, nullable=True)
    labels = Column(JSONB, nullable=True)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)
    received_at = Column(DateTime, nullable=True, index=True)
    synced_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="gmail_cache")
    
    __table_args__ = (
        {'postgresql_partition_by': None},
    )


class GCalCache(Base):
    """Cached Google Calendar events with embeddings"""
    __tablename__ = "gcal_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_id = Column(String(255), nullable=False)
    calendar_id = Column(String(255), nullable=True)
    title = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    location = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=True, index=True)
    end_time = Column(DateTime, nullable=True)
    attendees = Column(JSONB, nullable=True)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)
    synced_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="gcal_cache")


class GDriveCache(Base):
    """Cached Google Drive files with embeddings"""
    __tablename__ = "gdrive_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(String(255), nullable=False)
    name = Column(Text, nullable=True)
    mime_type = Column(String(255), nullable=True, index=True)
    parent_id = Column(String(255), nullable=True)
    content_preview = Column(Text, nullable=True)
    shared_with = Column(JSONB, nullable=True)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)
    modified_at = Column(DateTime, nullable=True, index=True)
    synced_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="gdrive_cache")


class SyncStatus(Base):
    """Track sync status per user and service"""
    __tablename__ = "sync_status"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    service = Column(String(50), nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    items_synced = Column(Integer, default=0)
    status = Column(String(50), default="idle")
    error_message = Column(Text, nullable=True)
