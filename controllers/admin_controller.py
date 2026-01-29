from fastapi import APIRouter,Depends,HTTPException, Request
from pydantic import BaseModel
from models.auth import User
from helpers.token_helper import get_current_user
from typing import Annotated 
from fastapi.responses import StreamingResponse
# from models.document import Document
import random 
import string
from fastapi import Request
import os 



admin_router = APIRouter()
