import asyncio
import json
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

import Services.drohneService as ds
import Services.replayService as rs
from Services.controlServices import ControlSession
from Services.keyboardSteuerung import set_key
from Services.input_ps5 import set_gamepad
from Services.input_touch import set_touch
from connect import log_command, label_flight, get_all_flight_names

router = APIRouter()


# --- Schemata für API-Anfragen ---
class FlightRequest(BaseModel):
    name: str


# Globaler Speicher für den Flugzeitraum
last_flight_times = {
    "start": None,
    "end": None
}

_ALLOWED_KEYS = {"w", "a", "s", "d", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "up", "down", "left", "right"}
_SPACE_KEYS = {" ", "Space", "Spacebar"}


# --- WebSockets für die Live-Steuerung ---

@router.websocket("/controlkeyboard")
async def ws_keyboard(ws: WebSocket):
    await ws.accept()
    if ds.ep_drone is None:
        await ws.send_json({"ok": False, "error": "Drone not connected"})
        await ws.close()
        return

    # Startzeit bei Verbindungsaufbau setzen
    last_flight_times["start"] = datetime.now()
    session = ControlSession(hz=20)
    await session.start()

    try:
        while True:
            msg = await ws.receive_json()
            key = msg.get("key")
            pressed = bool(msg.get("pressed", False))

            if key in _SPACE_KEYS and pressed:
                # 1. Replay-Abbruch (Not-Aus)
                if rs.active_replay_task and not rs.active_replay_task.done():
                    rs.active_replay_task.cancel()
                    rs.stop_drone_immediately()
                    await ws.send_json({"ok": True, "info": "Replay gestoppt"})
                else:
                    # 2. Normales Takeoff/Land
                    ok = await session.takeoff_land()
                    if ok:
                        # ENDZEIT BEIM LANDEN SPEICHERN
                        last_flight_times["end"] = datetime.now()
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
        await session.stop()


@router.websocket("/controlps")
async def ws_ps5(ws: WebSocket):
    await ws.accept()
    if ds.ep_drone is None:
        await ws.send_json({"ok": False, "error": "Drone not connected"})
        await ws.close()
        return

    last_flight_times["start"] = datetime.now()
    session = ControlSession(hz=20)
    await session.start()

    try:
        while True:
            msg = await ws.receive_json()

            # Landen/Starten via PS5 Button
            if msg.get("takeoffLand") is True:
                ok = await session.takeoff_land()
                if ok:
                    # ENDZEIT BEIM LANDEN SPEICHERN
                    last_flight_times["end"] = datetime.now()
                    log_command("FLIGHT_EVENT", "takeoff_land", source="ps5")
                await ws.send_json({"ok": ok})
                continue

            coords = {
                "lx": float(msg.get("lx", 0.0)), "ly": float(msg.get("ly", 0.0)),
                "rx": float(msg.get("rx", 0.0)), "l2": float(msg.get("l2", 0.0)), "r2": float(msg.get("r2", 0.0)),
            }
            set_gamepad(**coords)
            if any(v != 0.0 for v in coords.values()):
                log_command("PS5_MOVE", coords, source="ps5")
            await ws.send_json({"ok": True})
    except WebSocketDisconnect:
        pass
    finally:
        await session.stop()


@router.websocket("/controltouch")
async def ws_touch(ws: WebSocket):
    await ws.accept()
    if ds.ep_drone is None:
        await ws.send_json({"ok": False, "error": "Drone not connected"})
        await ws.close()
        return

    last_flight_times["start"] = datetime.now()
    session = ControlSession(hz=20)
    await session.start()

    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("takeoffLand") is True:
                ok = await session.takeoff_land()
                if ok:
                    # ENDZEIT BEIM LANDEN SPEICHERN
                    last_flight_times["end"] = datetime.now()
                    log_command("FLIGHT_EVENT", "takeoff_land", source="touch")
                await ws.send_json({"ok": ok})
                continue

            coords = {
                "lx": float(msg.get("lx", 0.0)), "ly": float(msg.get("ly", 0.0)),
                "rx": float(msg.get("rx", 0.0)), "ry": float(msg.get("ry", 0.0)),
            }
            set_touch(**coords)
            if any(v != 0.0 for v in coords.values()):
                log_command("TOUCH_MOVE", coords, source="touch")
            await ws.send_json({"ok": True})
    except WebSocketDisconnect:
        pass
    finally:
        await session.stop()


# --- HTTP Endpunkte ---

@router.post("/save-flight-name")
async def save_flight_name(req: FlightRequest):
    """Verknüpft den letzten Zeitraum (Start bis Landung) mit einem Namen."""
    start = last_flight_times["start"]
    end = last_flight_times["end"]

    # Falls die Drohne nie gelandet wurde (z.B. Tab geschlossen), nimm 'jetzt' als Fallback
    if not end:
        end = datetime.now()

    if start:
        label_flight(start, end, req.name)
        # Zeiten zurücksetzen für den nächsten Flug
        last_flight_times["start"] = None
        last_flight_times["end"] = None
        return {"ok": True, "message": f"Flug '{req.name}' gespeichert."}

    return {"ok": False, "message": "Keine Flugdaten gefunden."}


@router.get("/flights")
async def list_flights():
    """Gibt eine Liste aller benannten Flüge zurück."""
    try:
        names = get_all_flight_names()
        return {"ok": True, "flights": names}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/play-flight")
async def start_replay(req: FlightRequest):
    """Startet ein Replay basierend auf dem Namen."""
    if rs.active_replay_task and not rs.active_replay_task.done():
        return {"ok": False, "message": "Es läuft bereits ein Replay!"}

    rs.active_replay_task = asyncio.create_task(rs.play_flight(req.name))
    return {"ok": True, "message": f"Replay von '{req.name}' gestartet."}


@router.post("/emergency-stop")
async def emergency():
    """Bricht ein laufendes Replay ab und landet die Drohne sofort."""
    if rs.active_replay_task:
        rs.active_replay_task.cancel()
    rs.stop_drone_immediately()
    return {"ok": True, "message": "Not-Aus ausgeführt."}