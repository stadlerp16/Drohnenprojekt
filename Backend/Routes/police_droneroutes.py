# Routes/police_drone_routes.py
from fastapi import APIRouter
from Services.Steuerung.police_drone import police_drone_mode

router = APIRouter()


@router.post("/start")
async def start_police_mode():
    success = await police_drone_mode.start()
    if success:
        return {"status": "started", "active": True}
    return {
        "status": "error",
        "message": "Tracking läuft bereits oder keine Drohne verbunden",
        "active": police_drone_mode.is_active()
    }


@router.post("/stop")
async def stop_police_mode():
    success = await police_drone_mode.stop()
    return {
        "status": "stopped" if success else "not_running",
        "active": police_drone_mode.is_active()
    }


@router.get("/police_mode/status")
async def police_mode_status():
    return {"active": police_drone_mode.is_active()}