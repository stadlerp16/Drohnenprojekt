from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from Routes.drohnenRoutes import router as drohnen_router
from Services.drohneService import close
from Routes.steuerungRoutes import router as steuer_router
from connect import init_db  # <-- NEU: Importiere die DB-Initialisierung

import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def lifecycle(app: FastAPI):
    # START: Wird ausgeführt, wenn die FastAPI App hochfährt
    print("Starte MariaDB Initialisierung...")
    init_db()
    print("Datenbank bereit.")

    yield

    # END: Wird ausgeführt, wenn die App beendet wird
    print("Schließe Drohnen-Verbindung...")
    close()


app = FastAPI(lifespan=lifecycle)  # In FastAPI heißt das Argument meist 'lifespan'

# ... Rest deiner Middleware und Router ...
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(drohnen_router, prefix="/drone")
app.include_router(steuer_router, prefix="/drone")

if __name__ == "__main__":
    import uvicorn
    # Hier starten wir uvicorn programmatisch
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)