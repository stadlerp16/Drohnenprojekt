import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import Services.drohneService as ds
from datetime import datetime

from Services.controlServices import ControlSession
from Services.keyboardSteuerung import set_key
from Services.input_ps5 import set_gamepad
from Services.input_touch import set_touch
from Services.replayService import play_flight
from connect import log_command, label_flight, get_all_flight_names

router = APIRouter()

# Globaler Speicher für den letzten Flugzeitraum
last_flight_times = {
    "start": None,
    "end": None
}

_ALLOWED_KEYS = {
    "w", "a", "s", "d",
    "ArrowUp", "ArrowDown",
    "ArrowLeft", "ArrowRight",
    "up", "down", "left", "right",
}

_SPACE_KEYS = {" ", "Space", "Spacebar"}


@router.websocket("/controlkeyboard")
async def ws_keyboard(ws: WebSocket):
    await ws.accept()
    if ds.ep_drone is None:
        await ws.send_json({"ok": False, "error": "Drone not connected"})
        await ws.close()
        return

    # START-ZEIT festlegen
    last_flight_times["start"] = datetime.now()

    session = ControlSession(hz=20)
    await session.start()

    try:
        while True:
            msg = await ws.receive_json()
            key = msg.get("key")
            pressed = bool(msg.get("pressed", False))

            if key in _SPACE_KEYS and pressed:
                ok = await session.takeoff_land()
                log_command("FLIGHT_EVENT", "takeoff_land", source="keyboard")
                await ws.send_json({"ok": ok})
                continue

            if key in _ALLOWED_KEYS:
                set_key(key, pressed)
                if pressed:
                    log_command("KEYBOARD_MOVE", key, source="keyboard")

            await ws.send_json({"ok": True})
    except WebSocketDisconnect:
        pass
    finally:
        # END-ZEIT festlegen
        last_flight_times["end"] = datetime.now()
        await session.stop()


@router.websocket("/controlps")
async def ws_ps5(ws: WebSocket):
    await ws.accept()
    if ds.ep_drone is None:
        await ws.send_json({"ok": False, "error": "Drone not connected"})
        await ws.close()
        return

    # START-ZEIT festlegen
    last_flight_times["start"] = datetime.now()

    session = ControlSession(hz=20)
    await session.start()

    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("takeoffLand") is True:
                ok = await session.takeoff_land()
                log_command("FLIGHT_EVENT", "takeoff_land", source="ps5")
                await ws.send_json({"ok": ok})
                continue

            coords = {
                "lx": float(msg.get("lx", 0.0)),
                "ly": float(msg.get("ly", 0.0)),
                "rx": float(msg.get("rx", 0.0)),
                "l2": float(msg.get("l2", 0.0)),
                "r2": float(msg.get("r2", 0.0)),
            }
            set_gamepad(**coords)
            if any(v != 0.0 for v in coords.values()):
                log_command("PS5_MOVE", coords, source="ps5")
            await ws.send_json({"ok": True})
    except WebSocketDisconnect:
        pass
    finally:
        # END-ZEIT festlegen
        last_flight_times["end"] = datetime.now()
        await session.stop()


@router.websocket("/controltouch")
async def ws_touch(ws: WebSocket):
    await ws.accept()
    if ds.ep_drone is None:
        await ws.send_json({"ok": False, "error": "Drone not connected"})
        await ws.close()
        return

    # START-ZEIT festlegen
    last_flight_times["start"] = datetime.now()

    session = ControlSession(hz=20)
    await session.start()

    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("takeoffLand") is True:
                ok = await session.takeoff_land()
                log_command("FLIGHT_EVENT", "takeoff_land", source="touch")
                await ws.send_json({"ok": ok})
                continue

            coords = {
                "lx": float(msg.get("lx", 0.0)),
                "ly": float(msg.get("ly", 0.0)),
                "rx": float(msg.get("rx", 0.0)),
                "ry": float(msg.get("ry", 0.0)),
            }
            set_touch(**coords)
            if any(v != 0.0 for v in coords.values()):
                log_command("TOUCH_MOVE", coords, source="touch")
            await ws.send_json({"ok": True})
    except WebSocketDisconnect:
        pass
    finally:
        # END-ZEIT festlegen
        last_flight_times["end"] = datetime.now()
        await session.stop()


# NEUE ROUTE: Namen nachträglich vergeben
@router.post("/save-flight-name")
async def save_flight_name(data: dict):
    name = data.get("name", "Unbenannter Flug")

    start = last_flight_times["start"]
    end = last_flight_times["end"]

    if start and end:
        # Ruft deine Funktion in connect.py auf
        label_flight(start, end, name)
        return {"ok": True, "message": f"Flug als '{name}' gespeichert."}

    return {"ok": False, "message": "Keine Flugdaten zum Speichern gefunden."}

@router.get("/flights")
async def list_flights():
    try:
        names = get_all_flight_names()
        return {"ok": True, "flights": names}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.post("/play-flight")
async def play_flight_route(data: dict):
    name = data.get("name")
    # Wir starten das Replay als Hintergrundaufgabe, damit die Website nicht einfriert
    asyncio.create_task(play_flight(name))
    return {"ok": True, "message": f"Replay von '{name}' gestartet."}