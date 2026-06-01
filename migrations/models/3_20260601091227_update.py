from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" ADD "crop_growth_stage" VARCHAR(255);
        ALTER TABLE "user" ADD "farm_size" DOUBLE PRECISION;
        ALTER TABLE "user" ADD "crop_type" VARCHAR(255) NOT NULL  DEFAULT 'wheat';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" DROP COLUMN "crop_growth_stage";
        ALTER TABLE "user" DROP COLUMN "farm_size";
        ALTER TABLE "user" DROP COLUMN "crop_type";"""
