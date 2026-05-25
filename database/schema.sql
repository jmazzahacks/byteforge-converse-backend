-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- conversations: one row per chat thread between a user and the LLM.
-- user_id is an opaque identifier from the consuming app (auth is delegated).
CREATE TABLE IF NOT EXISTS conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         TEXT NOT NULL,
    title           TEXT NOT NULL,
    model           TEXT,
    system_prompt   TEXT,
    response_schema JSONB,
    created_at      BIGINT NOT NULL DEFAULT extract(epoch from now())::bigint,
    updated_at      BIGINT
);

-- Idempotent upgrades for databases created before these columns existed
-- (there is no migration framework yet; the setup script is re-runnable).
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS model           TEXT;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS system_prompt   TEXT;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS response_schema JSONB;

CREATE INDEX IF NOT EXISTS idx_conversations_user_id    ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);

COMMENT ON TABLE  conversations            IS 'A single chat thread between a user and the LLM';
COMMENT ON COLUMN conversations.user_id    IS 'Opaque user id from the consuming app — auth is delegated';
COMMENT ON COLUMN conversations.model      IS 'OpenRouter model id for this conversation; NULL falls back to BYTEFORGE_CONVERSE_LLM_MODEL';
COMMENT ON COLUMN conversations.system_prompt   IS 'Per-conversation system prompt encoding its purpose (form-filling, freeform, etc.)';
COMMENT ON COLUMN conversations.response_schema IS 'JSON schema for structured-output (JSON construction) conversations; NULL for freeform';
COMMENT ON COLUMN conversations.created_at IS 'Unix timestamp (epoch seconds) of creation';
COMMENT ON COLUMN conversations.updated_at IS 'Unix timestamp (epoch seconds) of last update';

-- messages: ordered turns within a conversation.
-- role mirrors the LLM convention (user / assistant / system / tool).
CREATE TABLE IF NOT EXISTS messages (
    id              UUID   PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID   NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT   NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content         TEXT   NOT NULL,
    token_count     INTEGER,
    created_at      BIGINT NOT NULL DEFAULT extract(epoch from now())::bigint
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id            ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id_created_at ON messages(conversation_id, created_at);

COMMENT ON TABLE  messages             IS 'A single message within a conversation';
COMMENT ON COLUMN messages.role        IS 'One of: user, assistant, system, tool';
COMMENT ON COLUMN messages.token_count IS 'Tokens consumed by this message, if known';
COMMENT ON COLUMN messages.created_at  IS 'Unix timestamp (epoch seconds) of creation';

-- sessions: short-lived frontend handshake records.
-- conversation_id may be NULL until the user starts a chat.
CREATE TABLE IF NOT EXISTS sessions (
    id              UUID   PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         TEXT   NOT NULL,
    conversation_id UUID            REFERENCES conversations(id) ON DELETE SET NULL,
    created_at      BIGINT NOT NULL DEFAULT extract(epoch from now())::bigint,
    expires_at      BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id    ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

COMMENT ON TABLE  sessions            IS 'Short-lived frontend handshake sessions';
COMMENT ON COLUMN sessions.user_id    IS 'Opaque user id from the consuming app — auth is delegated';
COMMENT ON COLUMN sessions.created_at IS 'Unix timestamp (epoch seconds) of creation';
COMMENT ON COLUMN sessions.expires_at IS 'Unix timestamp (epoch seconds) after which the session is invalid';
