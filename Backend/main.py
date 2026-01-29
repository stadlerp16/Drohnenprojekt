from fastapi import FastAPI
from Routes.drohnenRoutes import router as drohnen_router

app = FastAPI()

app.include_router(drohnen_router, prefix="/drone")

