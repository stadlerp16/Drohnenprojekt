from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import Services.drohneService as ds

from Services.controlServices import ControlSession
from Services.keyboardSteuerung import set_key
from Services.input_ps5 import set_gamepad

router = APIRouter()

_ALLOWED_KEYS = {
    "w","a","s","d",
    "ArrowUp","ArrowDown",
    "ArrowLeft","ArrowRight",
    "up","down","left","right",
}

_SPACE_KEYS = {" ", "Space", "Spacebar"}



@router.websocket("/controlkeyboard")
async def ws_keyboard(ws: WebSocket):
    await ws.accept()

    if ds.ep_drone is None:
        await ws.send_json({"ok": False, "error": "Drone not connected"})
        await ws.close()
        return

    session = ControlSession(hz=20)
    await session.start()

    try:
        while True:
            msg = await ws.receive_json()
            key = msg.get("key")
            pressed = bool(msg.get("pressed", False))

            if key in _SPACE_KEYS and pressed:
                ok = await session.takeoff_land()
                await ws.send_json({"ok": ok})
                continue

            if key in _ALLOWED_KEYS:
                set_key(key, pressed)

            await ws.send_json({"ok": True})

    except WebSocketDisconnect:
        pass
    finally:
        await session.stop()



@router.websocket("/controlps")
async def ws_ps5(ws: WebSocket):
    print("Hello Motherfucker")
    await ws.accept()

    if ds.ep_drone is None:
        await ws.send_json({"ok": False, "error": "Drone not connected"})
        await ws.close()
        return

    session = ControlSession(hz=20)
    await session.start()

    try:
        while True:
            msg = await ws.receive_json()

            # Button-Trigger vom Frontend (z.B. X)
            if msg.get("takeoffLand") is True:
                ok = await session.takeoff_land()
                await ws.send_json({"ok": ok})
                continue

            set_gamepad(
                lx=float(msg.get("lx", 0.0)),
                ly=float(msg.get("ly", 0.0)),
                rx=float(msg.get("rx", 0.0)),
                l2=float(msg.get("l2", 0.0)),
                r2=float(msg.get("r2", 0.0)),
            )

            await ws.send_json({"ok": True})

    except WebSocketDisconnect:
        pass
    finally:
        await session.stop()
