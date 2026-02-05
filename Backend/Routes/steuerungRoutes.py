# Routes/steuerungRoutes.py
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from Services.keyboardSteuerung import set_key, stop_all, control_loop, toggle_takeoff_land
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

            if key in (" ", "Space", "Spacebar") and pressed:
                loop = asyncio.get_running_loop()
                ok = await loop.run_in_executor(None, toggle_takeoff_land)
                await ws.send_json({"ok": ok})
                continue

            if key in ("w", "a", "s", "d", "ArrowUp", "ArrowDown", "up", "down"):
                set_key(key, pressed)

            await ws.send_json({"ok": True})

    except WebSocketDisconnect:
        pass
    finally:
        stop_event.set()
        await loop_task
        stop_all()
