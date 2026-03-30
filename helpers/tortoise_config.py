from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from contextlib import asynccontextmanager
from tortoise import Tortoise
# from helpers.pgvector import setup_vector_store
import os
        
TORTOISE_CONFIG = {
    'connections': {
        'default': os.getenv("DATABASE_URL")
        # 'default': "postgres://postgres:1234@localhost:5050/smartkisan"
    },
    "apps": {
        "models": {
            "models": [
                "models.auth",
                "models.api",
                "models.chat",
                # "models.document",
                "models.message",
                "models.suggestion",
                "aerich.models"
            ]
        }
    }
    }

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("TORTOISE_CONFIG:", TORTOISE_CONFIG)  # Add this before Tortoise.init
    await Tortoise.init(config=TORTOISE_CONFIG)
    from helpers.suggestion_scheduler import (
        shutdown_suggestion_scheduler,
        start_suggestion_scheduler,
    )

    start_suggestion_scheduler()
    yield
    shutdown_suggestion_scheduler()
    await Tortoise.close_connections()
