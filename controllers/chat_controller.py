from fastapi import APIRouter,Depends,HTTPException, Request
from pydantic import BaseModel
from models.auth import User
from helpers.token_helper import get_current_user
from typing import Annotated 
# from helpers.chat_chain import ask_question
from models.chat import Chat
from fastapi.responses import StreamingResponse
from models.message import Message
# from models.document import Document
import random 
import string
from fastapi import Request
import os 
from helpers.chat_chain import ask_question
from models.api import APIConfig

class ChatPayload(BaseModel):
    question:str
class UpdateChatNamePayload(BaseModel):
    name:str



chat_router = APIRouter()

@chat_router.post("/chat")
async def start_chat(
    data: ChatPayload,
    request: Request,
    user: Annotated[User, Depends(get_current_user)]
):
    try:
        # Create chat with random name
        random_suffix = ''.join(random.choices(string.ascii_uppercase, k=3))
        chat = await Chat.create(
            user=user,
            chat_name=f"Chat {random_suffix}"
        )

        stream_param = str(request.query_params.get("stream", "")).lower()
        if stream_param in ("1", "true", "yes"):
            async def responder():
                try:
                    final_text = ""
                    async for chunk in ask_question(request, data.question):
                        final_text += chunk
                        yield chunk.encode("utf-8")
                    await Message.create(chat=chat, question=data.question, answer=final_text)
                except Exception as e:
                    import logging
                    logging.exception("Error during streaming initial chat response")
                    raise

            # ✅ PASS HEADERS IN THE CONSTRUCTOR
            return StreamingResponse(
                responder(), 
                media_type="text/plain",
                headers={
                    "X-Chat-Id": str(chat.id),
                    "X-Chat-Name": chat.chat_name
                }
            )

        # Non-streaming fallback: collect full answer and return JSON
        response_text = ""
        async for chunk in ask_question(request, data.question):
            response_text += chunk

        await Message.create(chat=chat, question=data.question, answer=response_text)
        return {"success": True, "chat_id": chat.id, "chat_name": chat.chat_name, "answer": response_text}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@chat_router.get("/chats")
async def get_user_chats(user: Annotated[User, Depends(get_current_user)]):
    chats = await Chat.filter(user=user).order_by("-id").values(
        "id", "chat_name"
    )
    return {
        "success": True,
        "chats": chats
    }
    
@chat_router.get("/chat/{id}")
async def chat_now(id: str,user:Annotated[User,Depends(get_current_user)]):
    chat = await Chat.filter(id=id,user=user).first()
    if not chat:
        raise HTTPException(status_code=404,detail=f"Chat Not Found")
    try:
        response = []
        if chat.chat_name:
            name = chat.chat_name
            chat = await Message.filter(chat=chat).select_related("chat").order_by("id").all()
            response = [{"id":msg.id,"question":msg.question,"answer":msg.answer} for msg in chat]
        return {"success":True,"detail":"new chat created ","chat":response,"name":name}
    except Exception as error:
        raise HTTPException(status_code=500,detail=f"server error {error}")

@chat_router.post("/chat/{id}")
async def chat_now(id: int, data: ChatPayload, request: Request, user: Annotated[User, Depends(get_current_user)]):
    # Get chat and validate
    chat = await Chat.filter(id=id, user=user).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    try:
        stream_param = str(request.query_params.get("stream", "")).lower()
        if stream_param in ("1", "true", "yes"):
            async def responder():
                try:
                    final_text = ""
                    async for chunk in ask_question(request, data.question):
                        final_text += chunk
                        yield chunk.encode("utf-8")
                    # Save after streaming completes
                    if not chat.chat_name:
                        chat.chat_name = data.question[:50] + ("..." if len(data.question) > 50 else "")
                        await chat.save()
                    await Message.create(question=data.question, answer=final_text, chat=chat)
                except Exception as e:
                    import logging
                    logging.exception("Error during streaming chat response")
                    raise

            return StreamingResponse(responder(), media_type="text/plain")

        # Non-streaming
        response_text = ""
        async for chunk in ask_question(request, data.question):
            response_text += chunk

        if not chat.chat_name:
            chat.chat_name = data.question[:50] + ("..." if len(data.question) > 50 else "")
            await chat.save()
        await Message.create(question=data.question, answer=response_text, chat=chat)
        return {"answer": response_text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@chat_router.put("/chat/{id}")
async def chat_now(id: str,data:UpdateChatNamePayload,user:Annotated[User,Depends(get_current_user)]):
    chat = await Chat.filter(id=id,user=user).first()
    if not chat:
        raise HTTPException(status_code=404,detail=f"Chat Not Found")
    try:
        chat.chat_name=data.name 
        await chat.save()              
        return {"success":True,"detail":"Chat name updated"}
    except Exception as error:
        raise HTTPException(status_code=500,detail=f"server error {error}")
    
@chat_router.delete("/chat/{id}")
async def chat_now(id: str,user:Annotated[User,Depends(get_current_user)]):
    chat = await Chat.filter(id=id,user=user).first()
    if not chat:
        raise HTTPException(status_code=404,detail=f"Chat Not Found")
    try:
        await chat.delete()        
        return {"success":True,"detail":"Chat deleted"}
    except Exception as error:
        raise HTTPException(status_code=500,detail=f"server error {error}")