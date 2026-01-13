from fastapi import APIRouter, HTTPException, Depends, UploadFile, File,Form,BackgroundTasks
from typing import Annotated
from fastapi.responses import FileResponse
from pydantic import BaseModel
from models.auth import User
from helpers.token_helper import get_current_user
# from models.document import Document
from tortoise import Tortoise
from pathlib import Path
router = APIRouter()

# Document model is commented out - all Document-related code is disabled


class UpdateFilePayload(BaseModel):
    status:bool

ADMIN_USER_TYPE = 0
SUBADMIN_USER_TYPE = 1
REGULAR_USER_TYPE = 2

@router.get("/files")
async def get_uploaded_file(user:Annotated[User,Depends(get_current_user)]):
    if not user.user_type == ADMIN_USER_TYPE:
        raise HTTPException(status_code=403,detail="You are not allowed to  this action")
    
    try:
        # files = await Document.filter().order_by("-id").all()
        # return {"success":True,"file":files}
        return {"success":True,"file":[]}
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Server error {e}")
    
    
    
@router.put("/files/{id}")
async def get_uploaded_file(id: int, data:UpdateFilePayload,user:Annotated[User,Depends(get_current_user)]):
    if not user.user_type == ADMIN_USER_TYPE:
        raise HTTPException(status_code=403,detail="You are not allowed to  this action")
    
    try:
        # file = await Document.filter(id=id).first()
        # file.status = data.status
        # await file.save()
        # return {"success":True,"detail":"File updated successfully"}
        raise HTTPException(status_code=501,detail="Document functionality is disabled")
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Server error {e}")
    
    
@router.delete("/files/{id}")
async def get_uploaded_file(id: int, user:Annotated[User,Depends(get_current_user)]):
    if not user.user_type == ADMIN_USER_TYPE:
        raise HTTPException(status_code=403,detail="You are not allowed to  this action")
    # file = await Document.filter(id=id).first()
    # if not file:
    #     raise HTTPException(status_code=404,detail="No file found")
    try:
        # await Tortoise.get_connection("default").execute_query(f"DELETE FROM langchain_pg_embedding WHERE cmetadata->>'file_id' = '{file.id}';")
        # await Tortoise.get_connection("default").execute_query(
        #    f"DELETE FROM langchain_pg_embedding WHERE cmetadata->>'parent_document_id' = '{file.id}';")
        # await file.delete()
        # return {"success":True,"detail":"File deleted successfully"}
        raise HTTPException(status_code=501,detail="Document functionality is disabled")
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Server error {e}")
    
    
@router.get("/file/{id}")
async def get_uploaded_file(id: int, ):
    
    # file = await Document.filter(id=id).first()
    # if not file:
    #     raise HTTPException(status_code=404,detail="No file found")
    try:
        # file_path = Path(file.path).resolve()
        # if not file_path.exists():
        #     raise HTTPException(status_code=404, detail="File not found on server")
        # 
        # return FileResponse(
        # path=str(file_path),  
        # filename=file_path.name,  
        # media_type="application/pdf", 
        # headers={"Content-Disposition": "inline"}
        # )
        raise HTTPException(status_code=501,detail="Document functionality is disabled")
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Server error {e}")