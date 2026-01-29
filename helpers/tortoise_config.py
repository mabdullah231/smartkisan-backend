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
                "aerich.models"
            ]
        }
    }
    }

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("TORTOISE_CONFIG:", TORTOISE_CONFIG)  # Add this before Tortoise.init
    await Tortoise.init(config=TORTOISE_CONFIG)
    # app.state.vector_store = await setup_vector_store()
    # # print(app.state.vector_store)
    yield
    
    
