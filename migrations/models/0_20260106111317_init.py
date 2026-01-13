from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "phone" VARCHAR(15) NOT NULL,
    "phone_verified" BOOL NOT NULL  DEFAULT False,
    "password" VARCHAR(255) NOT NULL,
    "user_type" INT NOT NULL  DEFAULT 2,
    "is_active" BOOL NOT NULL  DEFAULT True
);
CREATE TABLE IF NOT EXISTS "codes" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "type" VARCHAR(255) NOT NULL,
    "value" TEXT NOT NULL,
    "expires_at" DATE NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    "updated_at" TIMESTAMPTZ NOT NULL,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "ai_config" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "api_key" VARCHAR(255) NOT NULL,
    "model_name" VARCHAR(255) NOT NULL,
    "prompt" TEXT
);
CREATE TABLE IF NOT EXISTS "chat" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "chat_name" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "message" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "question" VARCHAR(255) NOT NULL,
    "answer" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "chat_id" INT NOT NULL REFERENCES "chat" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
