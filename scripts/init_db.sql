-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    google_access_token TEXT,
    google_refresh_token TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    intent JSONB,
    response TEXT,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Gmail cache with embeddings
CREATE TABLE IF NOT EXISTS gmail_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    email_id VARCHAR(255) NOT NULL,
    thread_id VARCHAR(255),
    subject TEXT,
    sender VARCHAR(255),
    recipients JSONB,
    body_preview TEXT,
    labels JSONB,
    embedding vector(1536),
    received_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, email_id)
);

-- Google Calendar cache with embeddings
CREATE TABLE IF NOT EXISTS gcal_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    event_id VARCHAR(255) NOT NULL,
    calendar_id VARCHAR(255),
    title TEXT,
    description TEXT,
    location TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    attendees JSONB,
    embedding vector(1536),
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, event_id)
);

-- Google Drive cache with embeddings  
CREATE TABLE IF NOT EXISTS gdrive_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    file_id VARCHAR(255) NOT NULL,
    name TEXT,
    mime_type VARCHAR(255),
    parent_id VARCHAR(255),
    content_preview TEXT,
    shared_with JSONB,
    embedding vector(1536),
    modified_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, file_id)
);

-- Sync status tracking
CREATE TABLE IF NOT EXISTS sync_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    service VARCHAR(50) NOT NULL,
    last_sync_at TIMESTAMP,
    items_synced INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'idle',
    error_message TEXT,
    UNIQUE(user_id, service)
);

-- Create vector indexes for similarity search
CREATE INDEX IF NOT EXISTS gmail_embedding_idx ON gmail_cache 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS gcal_embedding_idx ON gcal_cache 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS gdrive_embedding_idx ON gdrive_cache 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Additional indexes for filtering
CREATE INDEX IF NOT EXISTS gmail_user_received_idx ON gmail_cache(user_id, received_at DESC);
CREATE INDEX IF NOT EXISTS gmail_sender_idx ON gmail_cache(sender);
CREATE INDEX IF NOT EXISTS gcal_user_time_idx ON gcal_cache(user_id, start_time);
CREATE INDEX IF NOT EXISTS gdrive_user_modified_idx ON gdrive_cache(user_id, modified_at DESC);
CREATE INDEX IF NOT EXISTS gdrive_mime_type_idx ON gdrive_cache(mime_type);
