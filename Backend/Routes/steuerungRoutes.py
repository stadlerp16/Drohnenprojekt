# Routes/steuerungRoutes.py
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from Services.keyboardSteuerung import set_key, stop_all, control_loop
import Services.drohneService as ds

router = APIRouter()

@router.websocket("/control")
async def ws_control(ws: WebSocket):
    await ws.accept()

    if ds.ep_drone is None:
        await ws.send_json({"ok": False, "error": "Drone not connected"})
        await ws.close()
        return

    stop_event = asyncio.Event()
    loop_task = asyncio.create_task(control_loop(stop_event, hz=20))

    try:
        while True:
            msg = await ws.receive_json()
            key = msg.get("key")
            pressed = bool(msg.get("pressed", False))

            if key in ("w", "a", "s", "d"):
                set_key(key, pressed)

            await ws.send_json({"ok": True})

    except WebSocketDisconnect:
        pass
    finally:
        stop_event.set()
        await loop_task
        stop_all()
