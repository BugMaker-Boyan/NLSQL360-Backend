from fastapi import APIRouter, UploadFile


dataset_router = APIRouter()


@dataset_router.get("/spider")
def test():
    return {"spider": "success"}



@dataset_router.post("/file")
async def upload_file(file: UploadFile):
    return {"uploadfile": file.filename}
