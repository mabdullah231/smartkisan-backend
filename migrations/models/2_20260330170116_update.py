from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "codes" ALTER COLUMN "updated_at" TYPE TIMESTAMPTZ USING "updated_at"::TIMESTAMPTZ;
        ALTER TABLE "codes" ALTER COLUMN "created_at" TYPE TIMESTAMPTZ USING "created_at"::TIMESTAMPTZ;
        ALTER TABLE "iot_configuration" ALTER COLUMN "created_at" TYPE TIMESTAMPTZ USING "created_at"::TIMESTAMPTZ;
        ALTER TABLE "iot_configuration" ALTER COLUMN "updated_at" TYPE TIMESTAMPTZ USING "updated_at"::TIMESTAMPTZ;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "codes" ALTER COLUMN "updated_at" TYPE TIMESTAMPTZ USING "updated_at"::TIMESTAMPTZ;
        ALTER TABLE "codes" ALTER COLUMN "created_at" TYPE TIMESTAMPTZ USING "created_at"::TIMESTAMPTZ;
        ALTER TABLE "iot_configuration" ALTER COLUMN "created_at" TYPE TIMESTAMPTZ USING "created_at"::TIMESTAMPTZ;
        ALTER TABLE "iot_configuration" ALTER COLUMN "updated_at" TYPE TIMESTAMPTZ USING "updated_at"::TIMESTAMPTZ;"""
