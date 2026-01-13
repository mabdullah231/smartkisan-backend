from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from typing import Annotated
from pydantic import BaseModel
# from langchain_community.document_loaders import PyPDFLoader
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from helpers.pgvector import setup_vector_store
from models.auth import User
from helpers.token_helper import get_current_user
# from models.document import Document
# from langchain_core.documents import Document as LangchainDocument
from models.ai import AI_Config
import uuid
# import httpx
# from helpers.document_loaders import  generate_conversational_summary
import os
import mimetypes
import re
# from bs4 import BeautifulSoup
# from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

router = APIRouter()

ADMIN_USER_TYPE = 0
SUBADMIN_USER_TYPE = 1
REGULAR_USER_TYPE = 2

# text_splitter = RecursiveCharacterTextSplitter(chunk_size=2500, chunk_overlap=100)
UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)
base_url = os.getenv("BASE_URL")

@router.post("/upload-file")
async def upload_file(
    background_tasks: BackgroundTasks,
    user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    file_type, _ = mimetypes.guess_type(file.filename)
    if not user.user_type == ADMIN_USER_TYPE:
        raise HTTPException(status_code=403, detail="You are not allowed to do this action")
    
    if file_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        if not os.path.exists(UPLOADS_DIR):
            os.makedirs(UPLOADS_DIR)
        
        file_path = os.path.join(UPLOADS_DIR, file.filename)
        name = file.filename
        
        f = open(file_path, "wb")
        f.write(await file.read())
        f.close()
        
        # database_document = await Document.create(name=name, user=user, path=file_path)
        
        # background_tasks.add_task(
        #     process_document_in_background, 
        #     file_path=file_path, 
        #     user=user, 
        #     database_document=database_document
        # )
        
        return {
            "success": True,
            "detail": "File uploaded successfully. Processing disabled.",
            # "document_id": database_document.id
        }
    
    except Exception as error:
        error_message = str(error).lower()
        if "api key" in error_message or "authentication" in error_message:
            raise HTTPException(status_code=401, detail="Invalid Gemini API key. Please check your API settings.")
        elif "quota exceeded" in error_message or "rate limit" in error_message:
            raise HTTPException(status_code=429, detail="Gemini quota exceeded. Please try again later.")
        elif "google" in error_message or "api error" in error_message:
            raise HTTPException(status_code=500, detail=f"Gemini API error: {str(error)}")
        else:
            raise HTTPException(status_code=500, detail=f"Error during file upload: {str(error)}")

# async def process_document_in_background(file_path: str, user: User, database_document: Document):
#     try:
#         loader = PyPDFLoader(file_path)
#         documents = await loader.aload()
        
#         page_content = documents[0].page_content
#         page_content = re.sub(r'\s+', ' ', page_content)
#         page_content = page_content.replace('\n', ' ').replace('\t', ' ').strip()
#         documents[0].page_content = page_content
        
#         api = await AI_Config.first()
#         print(api.api_key)
#         print(api.model_name)
#         summary = await generate_conversational_summary(documents, api.api_key, api.model_name)
        
#         summary_document = LangchainDocument(
#             page_content=summary,
#             metadata={
#                 "id": str(uuid.uuid4()),
#                 "user_id": user.id,
#                 "document_type": "summary",
#                 "parent_document_id": database_document.id
#             }
#         )
        
#         text_splitter = RecursiveCharacterTextSplitter(chunk_size=2500, chunk_overlap=100)
#         splitted_documents = await text_splitter.atransform_documents(documents)
        
#         for single_document in splitted_documents:
#             single_document.metadata["user_id"] = user.id
#             single_document.metadata["source"] = f"{base_url}/api/file/{database_document.id}"
#             single_document.metadata["file_id"] = database_document.id
#             single_document.metadata["file_name"] = database_document.name
#             single_document.metadata['document_type'] = "chunk"
#             single_document.metadata['chunk_id'] = str(uuid.uuid4())

#         vector_store = await setup_vector_store()
#         embeddings = await vector_store.aadd_documents(splitted_documents)
#         await vector_store.aadd_documents([summary_document], ids=[summary_document.metadata["id"]])

#     except Exception as error:
#         print("Error in background processing:", error)

