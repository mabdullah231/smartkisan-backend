from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" ADD "user_role" VARCHAR(255) NOT NULL  DEFAULT 'user';
        ALTER TABLE "user" DROP COLUMN "user_type";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" ADD "user_type" INT NOT NULL  DEFAULT 2;
        ALTER TABLE "user" DROP COLUMN "user_role";"""
