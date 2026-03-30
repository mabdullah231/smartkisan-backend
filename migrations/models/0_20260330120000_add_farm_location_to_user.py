from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "farm_latitude" DOUBLE PRECISION;
        ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "farm_longitude" DOUBLE PRECISION;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" DROP COLUMN IF EXISTS "farm_latitude";
        ALTER TABLE "user" DROP COLUMN IF EXISTS "farm_longitude";"""
