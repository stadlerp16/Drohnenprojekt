import asyncio
import json
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

import Services.DrohneVerwaltung.drohneService as ds
import Services.DrohneVerwaltung.telemtrieService as ts
import Services.Steuerung.replayService as rs
from Services.Steuerung.controlServices import ControlSession
from Services.Steuerung.keyboardSteuerung import set_key
from Services.Steuerung.input_ps5 import set_gamepad
from Services.Steuerung.input_touch import set_touch
from connect import log_command, get_all_flight_names

router = APIRouter()


class FlightRequest(BaseModel):
    name: str


# Lokale Hilfsvariable für Tastendruck-Dauer
key_press_times = {}

_ALLOWED_KEYS = {"w", "a", "s", "d", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "up", "down", "left", "right"}
_SPACE_KEYS = {" ", "Space", "Spacebar"}


async def handle_takeoff_logic(source: str, session: ControlSession):
    if await session.takeoff_land():
        log_command("FLIGHT_EVENT", "takeoff_land", source=source)

        if not ts.is_logging_allowed:
            # Flug startet
            ts.reset_tracking()
            ts.current_flight_start = datetime.now()
            asyncio.create_task(ts.start_takeoff_timer(2.0))
        else:
            # Flug endet
            ts.is_logging_allowed = False
            ts.last_completed_flight = {
                "start": ts.current_flight_start,
                "end": datetime.now()
            }
            ts.current_flight_start = None


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
            key, pressed = msg.get("key"), bool(msg.get("pressed", False))

            if key in _SPACE_KEYS and pressed:
                await handle_takeoff_logic("keyboard", session)
                continue

            if key in _ALLOWED_KEYS:
                set_key(key, pressed)
                # Nur tracken, wenn der Timer abgelaufen ist
                if ts.is_logging_allowed:
                    if pressed:
                        if key not in key_press_times:
                            key_press_times[key] = datetime.now()
                    else:
                        start_t = key_press_times.pop(key, None)
                        if start_t:
                            dur = (datetime.now() - start_t).total_seconds()
                            # POSITION IN DER MAP AKTUALISIEREN
                            ts.update_position_keyboard(key, dur)
                            log_command("KEYBOARD_DURATION", json.dumps({"key": key, "duration": dur}),
                                        source="keyboard")

            await ws.send_json({"ok": True})
    except WebSocketDisconnect:
        pass
    finally:
        await session.stop()


@router.websocket("/controlps")
async def ws_ps5(ws: WebSocket):
    await ws.accept()
    session = ControlSession(hz=20)
    await session.start()
    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("takeoffLand") is True:
                await handle_takeoff_logic("ps5", session)
                continue

            coords = {k: float(msg.get(k, 0.0)) for k in ["lx", "ly", "rx", "l2", "r2"]}
            set_gamepad(**coords)

            if ts.is_logging_allowed and any(abs(v) > 0.05 for v in coords.values()):
                # ANALOGE POSITION IN DER MAP AKTUALISIEREN
                ts.update_position_analog(coords["lx"], coords["ly"])
                log_command("PS5_MOVE", coords, source="ps5")
    except WebSocketDisconnect:
        pass
    finally:
        await session.stop()


@router.websocket("/controltouch")
async def ws_touch(ws: WebSocket):
    await ws.accept()
    session = ControlSession(hz=20)
    await session.start()
    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("takeoffLand") is True:
                await handle_takeoff_logic("touch", session)
                continue

            coords = {k: float(msg.get(k, 0.0)) for k in ["lx", "ly", "rx", "ry"]}
            set_touch(**coords)

            if ts.is_logging_allowed and any(abs(v) > 0.05 for v in coords.values()):
                # ANALOGE POSITION IN DER MAP AKTUALISIEREN
                ts.update_position_analog(coords["lx"], coords["ly"])
                log_command("TOUCH_MOVE", coords, source="touch")
    except WebSocketDisconnect:
        pass
    finally:
        await session.stop()


@router.post("/play-flight")
async def start_replay(req: FlightRequest):
    if rs.active_replay_task and not rs.active_replay_task.done():
        return {"ok": False}
    rs.active_replay_task = asyncio.create_task(rs.play_flight(req.name))
    return {"ok": True}


@router.post("/emergency-stop")
async def emergency():
    if rs.active_replay_task:
        rs.active_replay_task.cancel()
    rs.stop_drone_immediately()
    return {"ok": True}

