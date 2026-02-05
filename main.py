from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from helpers.tortoise_config import lifespan
from controllers.auth_controller import auth_router
from controllers.settings_controller import settings_router
from controllers.user_controller import user_router
from fastapi.middleware.cors import CORSMiddleware
from controllers.file_controller import router as kbs_router
from controllers.file_crud_controller import router as files_router
from controllers.chat_controller import chat_router
from controllers.admin_controller import admin_router
# from controllers.vector_db_controller import router as vector_db_router
# from controllers.scraper_controller import router as scraper_router
# from controllers.disease_controller import disease_router



app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Chat-Id", "X-Chat-Name"]
)

app.include_router(auth_router, prefix='/api', tags=['Authentication'])
app.include_router(settings_router, prefix='/api', tags=['Settings'])
app.include_router(user_router, prefix='/api', tags=['Users'])
app.include_router(kbs_router, prefix='/api', tags=['Knowledge Base'])
app.include_router(files_router, prefix='/api', tags=['Uploaded Files'])
app.include_router(chat_router, prefix='/api', tags=['Chat'])
app.include_router(admin_router, prefix='/api', tags=['Admin'])
# app.include_router(vector_db_router, prefix='/api', tags=['Vector DB'])
# app.include_router(scraper_router, prefix='/api', tags=['Scraper'])
# app.include_router(disease_router, prefix='/api', tags=['Disease Detector'])

@app.get('/')
def greetings():
    return {
        "Message": "Hello Developers, how are you :)"
    }