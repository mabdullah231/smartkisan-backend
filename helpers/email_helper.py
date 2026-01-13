from typing import Literal, Union, Tuple, Annotated
from models.auth import User, Code
from fastapi import HTTPException
from datetime import datetime, timedelta
# from helpers.email_generator import send_email, send_confirmation_email, send_reset_email, confirmation_email  # Email functionality disabled - using phone
import random




def send_reset_email(to_phone: str, code: Union[str, int]) -> bool:
    """
    Send a password reset code to the user (via phone).

    Args:
        to_phone (str): The recipient phone number.
        code (Union[str, int]): The reset code.

    Returns:
        bool: True if the code was sent successfully, False otherwise.
    """
    # Note: This function is kept for compatibility but email sending is disabled
    # In production, you would integrate with an SMS service here
    print(f"Sending reset code {code} to phone: {to_phone}")
    return True




async def generate_code(type: Literal["password_reset", "account_activation"], user: User) -> Tuple[Code, bool]:
    """
    Generates a code for account actions and sends the corresponding code via phone.

    Args:
        type (Literal["password_reset", "account_activation"]): The type of code to generate.
        user (User): The user for whom the code is generated.

    Returns:
        Tuple[Code, bool]: The created Code instance and a boolean indicating if the code was sent successfully.
    """
    try:
        code_value = str(random.randint(1000, 9999))
        code = Code(
            type=type,
            value=code_value,
            expires_at=datetime.utcnow() + timedelta(minutes=40),
            user=user
        )
        print(f"User Phone: {user.phone}")
        print(f"Verification Code: {code_value}")
        await code.save()
        # if type == "password_reset":
        #     phone_sent = send_reset_email(user.phone, code_value)
        # elif type == "account_activation":
        #     phone_sent = send_confirmation_email(user.phone, code_value)
        # else:
        #     raise ValueError("Invalid code type provided.")

        # In production, integrate with SMS service here
        # return phone_sent
        return True
    except Exception as e:
        # db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to generate code: {e}")

