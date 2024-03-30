from fastapi import FastAPI
import uvicorn
from apps.user.router import user_router
from apps.auth.auth_token import auth_router
from apps.dataset.router import dataset_router
from tortoise.contrib.fastapi import register_tortoise
from settings import TORTIOSE_CONFIG


app = FastAPI()

register_tortoise(
    app=app,
    config=TORTIOSE_CONFIG
)

app.include_router(user_router, prefix="/user", tags=["user_api"])
app.include_router(auth_router, prefix="/auth", tags=["auth_api"])
app.include_router(dataset_router, prefix="/dataset", tags=["dataset_api"])


if __name__ == "__main__":
    uvicorn.run("main:app", port=8080, reload=True)
    