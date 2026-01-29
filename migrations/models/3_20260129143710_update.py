from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "apiconfig" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "category" VARCHAR(50) NOT NULL,
    "provider" VARCHAR(100) NOT NULL,
    "api_key" VARCHAR(512),
    "base_url" VARCHAR(255),
    "extra_config" JSONB,
    "is_active" BOOL NOT NULL  DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
        DROP TABLE IF EXISTS "api_config";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "apiconfig";"""
