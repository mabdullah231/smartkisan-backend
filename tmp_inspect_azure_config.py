import os
import asyncio
from dotenv import load_dotenv
load_dotenv()
from tortoise import Tortoise
from models.api import APIConfig

async def run():
    await Tortoise.init(config={
        'connections': {'default': os.getenv('DATABASE_URL')},
        'apps': {'models': {'models': ['models.api'], 'default_connection': 'default'}}
    })
    configs = await APIConfig.filter(category='Azure', is_active=True).all()
    if not configs:
        print('NO AZURE CONFIG FOUND')
    for c in configs:
        print('ID:', c.id)
        print('provider:', c.provider)
        print('base_url:', c.base_url)
        print('api_key:', 'SET' if c.api_key else 'NONE')
        print('extra_config:', c.extra_config)
        print('is_active:', c.is_active)
        print('----')
    await Tortoise.close_connections()

asyncio.run(run())
