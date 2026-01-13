from fastapi import APIRouter, HTTPException, Depends
from argon2 import PasswordHasher
from pydantic import BaseModel, Field, field_validator
from typing import Annotated,Optional
from models.auth import User, Code
from helpers.email_helper import generate_code
# from helpers.email_generator import confirmation_email  # Email functionality disabled - using phone
from helpers.token_helper import generate_user_token,get_current_user
from helpers.phone_validator import validate_pakistani_phone

auth_router = APIRouter()

ph = PasswordHasher()


class SignupPayload(BaseModel):
    name: str
    phone: str
    password: str
    user_role: str = "user"
    
    @field_validator('phone', mode='before')
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            raise ValueError("Phone number is required")
        return validate_pakistani_phone(str(v))

class LoginPayload(BaseModel):
    phone: str
    password: str
    
    @field_validator('phone', mode='before')
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            raise ValueError("Phone number is required")
        return validate_pakistani_phone(str(v))

class AccountVerificationPayload(BaseModel):
    user_id: int
    code: int

class PasswordResetCode(BaseModel):
    phone: str
    
    @field_validator('phone', mode='before')
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            raise ValueError("Phone number is required")
        return validate_pakistani_phone(str(v))

class VerifyCodePayload(BaseModel):
    phone: str
    code: str
    
    @field_validator('phone', mode='before')
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            raise ValueError("Phone number is required")
        return validate_pakistani_phone(str(v))
    
class ResetCodePayload(BaseModel):
    phone: str
    password: str
    
    @field_validator('phone', mode='before')
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            raise ValueError("Phone number is required")
        return validate_pakistani_phone(str(v))
    
class UpdateProfilePayload(BaseModel):
    phone: Optional[str] = None
    name: Optional[str] = None
    password: Optional[str] = None
    
    @field_validator('phone', mode='before')
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            return v
        return validate_pakistani_phone(str(v))


@auth_router.post('/signup')
async def  signup(payload: SignupPayload):
    user = await User.filter(phone = payload.phone).first()
    print(f"Payload: {payload}")
    if user: 
        print(f"User already exists: {user}")
        raise HTTPException(status_code=400, detail="User already exists")
    try:
        user = User(
            name = payload.name,
            phone = payload.phone,  # Already validated and normalized to 03XXXXXXXXX format
            password = ph.hash(payload.password),
            user_role = payload.user_role
        )
        await user.save()
        await generate_code("account_activation", user=user)
        # is_phone_sent:bool = 
        # if(is_phone_sent):
        token = generate_user_token({ "id": user.id })
        print(f"Toeken: ", token)
        return {
            "success": True, 
            "verify": False,
            "user_id": user.id,
            "detail": "Verification code sent successfully" ,   
        }
        # else:
        #     await user.delete()
    except ValueError as e:
        # Validation errors from phone validator
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400,detail=f"server error {e}")
    
@auth_router.post("/signin")
async def signin(data: LoginPayload):
    user = await User.filter(phone=data.phone).first()
    if not user:
        raise HTTPException(
            status_code=400, 
            detail="User Not found"
        )
    
    try:
        is_varified = ph.verify(user.password, data.password)
        print(f"IS Varified: {is_varified}")
    except:
        raise HTTPException(
            status_code=400, 
            detail="Invalid Credentials."
        )
        
    if user.phone_verified == False:
        is_phone_sent:bool = await generate_code("account_activation", user=user)
        if is_phone_sent:
            return  {
                "success":True,
                "verify": False,
                "user_id": user.id,
                "detail":"Phone not verified verification code sent successfully"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Phone not verified verification code not sent")
    try:
        token = generate_user_token({ "id": user.id })
        
        return { 
            "success": True,
            "token": token,
            "user": {
                'name': user.name,
                'phone': user.phone,
                'user_role': user.user_role
            },
            "detail":"Login Successfully"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail= str(e)
        )


@auth_router.delete("/delete-account")
async def delete_account(user: Annotated[User, Depends(get_current_user)],):
    try:
        await user.delete()
        return {
            "success": True,
            "detail": "Account deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@auth_router.post("/account-verification")
async def account_verificatoin(payload: AccountVerificationPayload):
    user = await User.filter(id=payload.user_id).first()
    if not user:
        raise HTTPException("User not found")
    print(f"Payload: {payload.code}")
    code = await Code.filter(user__id=user.id).order_by("-id").first()
    
    if not code:
        raise HTTPException(detail="Invalid code", status_code=400)
    try:
        if (code.value == str(payload.code)):
            print("Code matched")
            user.phone_verified = True
            await user.save()
            # confirmation_email(to_phone=user.phone)
            await code.delete()
            token = generate_user_token({ "id": user.id })
            return {
                "success": True,
                "token": token,
                "user": {
                    'name': user.name,
                    'phone': user.phone,
                    'user_role': user.user_role,
                },
                "detail": "Account verified successfully"
            }
        else:
            raise HTTPException(detail="Invalid code", status_code=400)
    except Exception as e:
        raise HTTPException(detail="Invalid code", status_code=400)



@auth_router.post("/resend-otp")
async def password_reset_code(payload: PasswordResetCode):
    user = await User.filter(phone=payload.phone).first()
    if not user:
        raise HTTPException(detail="Account not found ", status_code=400)
    try:
        await generate_code("account_activation", user)
        return {
            "success": True,
            "detail": "Account activation code sent successfully"
        }
    except Exception as e:
        raise HTTPException(detail=str(e), status_code=500)
    
@auth_router.post("/password-reset-code")
async def password_reset_code(payload: PasswordResetCode):
    user = await User.filter(phone=payload.phone).first()
    if not user:
        raise HTTPException(detail="Account not found ", status_code=400)
    try:
        await generate_code("password_reset", user)
        return {
            "success": True,
            "detail": "Password reset code sent successfully"
        }
    except Exception as e:
        raise HTTPException(detail=str(e), status_code=500)




@auth_router.post("/confirm-otp")
async def reset_password(payload: VerifyCodePayload):
    user = await User.filter(phone=payload.phone).first()
    if not user:
        raise HTTPException(detail="User not found", status_code=400)
    if user:
        code  = await Code.filter(user__id=user.id, type="password_reset").order_by("-id").first()
        if payload.code == code.value:
            code.delete()
            return {
                "success": True,
                "user_id": user.id,
                "detail": "Otp verified successfully"
            }
        else:
            raise HTTPException(detail="Invalid code", status_code=400)
    else:
        raise HTTPException(detail="User not found", status_code=400)
    
    
@auth_router.get("/validate-token")
async def reset_password(user: Annotated[User, Depends(get_current_user)]):
   
    if not user:
        raise HTTPException(detail="Un Authenticated", status_code=401)
    if user:
        return {
            "success": True,
            "detail": "Token verified successfully"
        } 
    
    
    
@auth_router.post("/reset-password")
async def reset_password(payload: ResetCodePayload):
    try:
        user = await User.filter(phone=payload.phone).first()
        if user:
            hashed_password = ph.hash(payload.password)
            user.password = hashed_password
            await user.save()
            return {
                "success": True,
                "detail": "Password reset successfully"
            }
        else:
            raise HTTPException(detail="User not found", status_code=400)
    except Exception as e:
        raise HTTPException(detail=str(e), status_code=400)
    
    
@auth_router.post("/update-profile")
async def reset_password(data: UpdateProfilePayload,user:Annotated[User,Depends(get_current_user)]):
    if data.phone:
        if await User.filter(phone=data.phone).first():
            if data.phone != user.phone:
                raise HTTPException(detail="Phone already exists", status_code=400)
        
    if data.password:
        try:
            ph.verify(user.password,data.password)
        except:
            raise HTTPException(status_code=403,detail="Current password is incorrect")
    try:
        if data.password:
            hashed_password = ph.hash(data.password)
            user.password = hashed_password
        if data.name:
             user.name = data.name
        if data.phone:
            user.phone = data.phone
        await user.save()
        return {
            "success": True,
            "data": {
                "name": user.name,
                "phone": user.phone,
            },
            "detail": "Profile updated successfully"
        }
            
    except Exception as e:
        raise HTTPException(detail=str(e), status_code=400)
    
    
    
   
