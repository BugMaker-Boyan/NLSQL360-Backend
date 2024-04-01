from fastapi import APIRouter, Form
from app.user.models import User
from app.auth.auth_token import get_password_hash, UserObject, UserInDBObject, Depends, get_current_user
from app.global_enums import *
from pydantic import BaseModel


user_router = APIRouter()


@user_router.get("/", response_model=UserObject)
async def get_info(current_user: UserObject = Depends(get_current_user)):
    user = await User.get(username=current_user.username)
    return user


@user_router.post("/")
async def register(username: str = Form(), 
                   password: str = Form(),
                   email: str = Form()):
    await User.create(
        username=username,
        hashed_password=get_password_hash(password),
        email=email
    )
    return SUCCESS_COMPLETE


class LLMAPIConfigObject(BaseModel):
    llm_api_config_baseurl: str
    llm_api_config_key: str


@user_router.put("/llm_api_config")
async def modify_llm_api_config(api_config: LLMAPIConfigObject, current_user: UserObject = Depends(get_current_user)):
    config_dict = api_config.model_dump()
    await User.filter(username=current_user.username).update(**config_dict)
    return SUCCESS_COMPLETE


class UserPasswordObject(BaseModel):
    password: str
    

@user_router.put("/password")
async def modify_password(user_password: UserPasswordObject, current_user: UserObject = Depends(get_current_user)):
    await User.filter(username=current_user.username).update(hashed_password=get_password_hash(user_password.password))
    return SUCCESS_COMPLETE


class UserEmailObject(BaseModel):
    password: str


@user_router.put("/email")
async def modify_email(user_email: UserEmailObject, current_user: UserObject = Depends(get_current_user)):
    await User.filter(username=current_user.username).update(email=user_email.email)
    return SUCCESS_COMPLETE
