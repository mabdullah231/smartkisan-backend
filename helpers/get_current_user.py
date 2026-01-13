from models.auth import User, Token
from fastapi import HTTPException
async def get_user_from_token(token: str) -> User:
    # Retrieve the token along with the associated user in a single query
    token_db = await Token.filter(token=token).select_related("user").first()
    if token_db is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = token_db.user
    if user is None:
        raise HTTPException(
            status_code=400,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user