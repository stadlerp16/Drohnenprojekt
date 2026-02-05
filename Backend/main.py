from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from Routes.drohnenRoutes import router as drohnen_router
from  Services.drohneService import close
from Routes.steuerungRoutes import router as steuer_router



async def lifecycle(app: FastAPI):
    #start
    yield
    #end
    close()

app = FastAPI(lifecycle=lifecycle)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(drohnen_router, prefix="/drone")
app.include_router(steuer_router, prefix="/drone")
