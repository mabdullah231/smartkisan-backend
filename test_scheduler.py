import asyncio
from dotenv import load_dotenv
load_dotenv()
from tortoise import Tortoise
from helpers.tortoise_config import TORTOISE_CONFIG
from helpers.suggestion_generator import run_suggestion_job_for_all_users

async def main():
    await Tortoise.init(config=TORTOISE_CONFIG)
    try:
        ok, fail = await run_suggestion_job_for_all_users()
        print(f"Generated: {ok}, Failed: {fail}")
    finally:
        await Tortoise.close_connections()

asyncio.run(main())