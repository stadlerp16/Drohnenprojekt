import asyncio
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

import Services.DrohneVerwaltung.drohneService as ds
import Services.Steuerung.replayService as rs
from Services.Steuerung.controlServices import ControlSession
from Services.Steuerung.keyboardSteuerung import set_key
from Services.Steuerung.input_ps5 import set_gamepad
from Services.Steuerung.input_touch import set_touch
from connect import log_command, label_flight, get_all_flight_names

router = APIRouter()

# --- Status-Management ---
is_logging_allowed = False
current_flight_start = None
last_completed_flight = {"start": None, "end": None}
key_press_times = {}

async def start_takeoff_timer(duration: float = 2.0):
    global is_logging_allowed
    is_logging_allowed = False
    await asyncio.sleep(duration)
    is_logging_allowed = True
    print("[SYSTEM] Aufnahme gestartet!")

class FlightRequest(BaseModel):
    name: str

_ALLOWED_KEYS = {"w", "a", "s", "d", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "up", "down", "left", "right"}
_SPACE_KEYS = {" ", "Space", "Spacebar"}

@router.websocket("/controlkeyboard")
async def ws_keyboard(ws: WebSocket):
    global is_logging_allowed, current_flight_start, last_completed_flight
    await ws.accept()
    if ds.ep_drone is None:
        await ws.send_json({"ok": False, "error": "Drone not connected"}); await ws.close(); return

    session = ControlSession(hz=20)
    await session.start()

    try:
        while True:
            msg = await ws.receive_json()
            key, pressed = msg.get("key"), bool(msg.get("pressed", False))

            if key in _SPACE_KEYS and pressed:
                ok = await session.takeoff_land()
                if ok:
                    log_command("FLIGHT_EVENT", "takeoff_land", source="keyboard")
                    if not is_logging_allowed:
                        current_flight_start = datetime.now()
                        asyncio.create_task(start_takeoff_timer(2.0))
                    else:
                        is_logging_allowed = False
                        last_completed_flight = {"start": current_flight_start, "end": datetime.now()}
                        current_flight_start = None
                continue

            if key in _ALLOWED_KEYS:
                set_key(key, pressed)
                if is_logging_allowed:
                    if pressed:
                        if key not in key_press_times: key_press_times[key] = datetime.now()
                    else:
                        start_t = key_press_times.pop(key, None)
                        if start_t:
                            dur = (datetime.now() - start_t).total_seconds()
                            log_command("KEYBOARD_DURATION", json.dumps({"key": key, "duration": dur}), source="keyboard")
            await ws.send_json({"ok": True})
    except WebSocketDisconnect: pass
    finally: is_logging_allowed = False; await session.stop()

@router.websocket("/controlps")
async def ws_ps5(ws: WebSocket):
    global is_logging_allowed, current_flight_start, last_completed_flight
    await ws.accept()
    session = ControlSession(hz=20); await session.start()
    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("takeoffLand") is True:
                ok = await session.takeoff_land()
                if ok:
                    log_command("FLIGHT_EVENT", "takeoff_land", source="ps5")
                    if not is_logging_allowed:
                        current_flight_start = datetime.now()
                        asyncio.create_task(start_takeoff_timer(2.0))
                    else:
                        is_logging_allowed = False
                        last_completed_flight = {"start": current_flight_start, "end": datetime.now()}
                        current_flight_start = None
                continue
            coords = {k: float(msg.get(k, 0.0)) for k in ["lx", "ly", "rx", "l2", "r2"]}
            set_gamepad(**coords)
            if is_logging_allowed and any(abs(v) > 0.05 for v in coords.values()):
                log_command("PS5_MOVE", coords, source="ps5")
    except WebSocketDisconnect: pass
    finally: await session.stop()

@router.websocket("/controltouch")
async def ws_touch(ws: WebSocket):
    global is_logging_allowed, current_flight_start, last_completed_flight
    await ws.accept()
    session = ControlSession(hz=20); await session.start()
    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("takeoffLand") is True:
                ok = await session.takeoff_land()
                if ok:
                    log_command("FLIGHT_EVENT", "takeoff_land", source="touch")
                    if not is_logging_allowed:
                        current_flight_start = datetime.now()
                        asyncio.create_task(start_takeoff_timer(2.0))
                    else:
                        is_logging_allowed = False
                        last_completed_flight = {"start": current_flight_start, "end": datetime.now()}
                        current_flight_start = None
                continue
            coords = {k: float(msg.get(k, 0.0)) for k in ["lx", "ly", "rx", "ry"]}
            set_touch(**coords)
            if is_logging_allowed and any(abs(v) > 0.05 for v in coords.values()):
                log_command("TOUCH_MOVE", coords, source="touch")
    except WebSocketDisconnect: pass
    finally: await session.stop()

@router.post("/save-flight-name")
async def save_flight_name(req: FlightRequest):
    global last_completed_flight
    s, e = last_completed_flight["start"], last_completed_flight["end"]
    if s and e:
        label_flight(s - timedelta(seconds=5), e + timedelta(seconds=1), req.name)
        last_completed_flight = {"start": None, "end": None}
        return {"ok": True, "message": f"Flug '{req.name}' gespeichert."}
    return {"ok": False, "message": "Kein abgeschlossener Flug gefunden."}



@router.post("/play-flight")
async def start_replay(req: FlightRequest):
    if rs.active_replay_task and not rs.active_replay_task.done(): return {"ok": False}
    rs.active_replay_task = asyncio.create_task(rs.play_flight(req.name))
    return {"ok": True}

@router.post("/emergency-stop")
async def emergency():
    if rs.active_replay_task: rs.active_replay_task.cancel()
    rs.stop_drone_immediately()
    return {"ok": True}