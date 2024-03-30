from fastapi import APIRouter, Form
# from pydantic import BaseModel\


# class User(BaseModel):
#     username: str
#     password: str


user_router = APIRouter()


@user_router.get("/info")
def get_info(username):
    return {
        "username": username
    }


@user_router.get("/info_with_default")
def get_info(username="default"):
    return {
        "username": username
    }


# @user_router.post("/login")
# def login(user: User):
#     print(user)
#     return user


@user_router.post("/login")
def login(username: str = Form(), password: str = Form()):
    return {
        "username": username
    }