from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
async def root():
    return {"message": "Hello World"}