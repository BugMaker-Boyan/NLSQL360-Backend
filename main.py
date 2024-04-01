from fastapi import FastAPI
import uvicorn
from app.service.user.router import user_router
from app.service.auth.auth_token import auth_router
from app.service.dataset.router import dataset_router
from app.service.evaluation.router import evaluation_router
from tortoise.contrib.fastapi import register_tortoise
from settings import TORTIOSE_CONFIG
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

register_tortoise(
    app=app,
    config=TORTIOSE_CONFIG
)

app.include_router(user_router, prefix="/user", tags=["user_api"])
app.include_router(auth_router, prefix="/auth", tags=["auth_api"])
app.include_router(dataset_router, prefix="/dataset", tags=["dataset_api"])
app.include_router(evaluation_router, prefix="/evaluation", tags=["evaluation_api"])


if __name__ == "__main__":
    uvicorn.run("main:app", port=8080, reload=True)
    