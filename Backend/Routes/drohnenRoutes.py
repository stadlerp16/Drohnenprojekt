import asyncio
from datetime import datetime, timedelta
from fastapi import APIRouter, Body, HTTPException, WebSocket, WebSocketDisconnect
from urllib import request

from fastapi import APIRouter, Body, HTTPException
import ipaddress
from pydantic import BaseModel
from starlette.websockets import WebSocket

import Services.DrohneVerwaltung.drohneService as drohne_service
import Services.DrohneVerwaltung.telemtrieService as telemtrie_service
from connect import get_all_flight_names
from pydantic import BaseModel
from typing import List

from connect import label_flight, get_all_flight_names
router = APIRouter()
class FlightRequest(BaseModel): name: str


@router.post("/connect")
def connect_drone(ip: str = Body(..., embed=True)):
    # IPv4 validieren
    try:
        ip_obj = ipaddress.IPv4Address(ip.strip())
    except ipaddress.AddressValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "Ungültige IPv4-Adresse. Beispiel: 192.168.0.10"
            }
        )

    ip_str = str(ip_obj)

    # Wenn bereits verbunden -> erst sauber antworten, dann verzögert restarten
    if drohne_service.is_connected():
        drohne_service.delayed_restart(ip_str, delay=0.5)
        return {
            "status": "ok",
            "message": f"Server startet neu und verbindet erneut mit {ip_str}",
            "restarting": True
        }

    # Normale Verbindung aufbauen
    ok = drohne_service.buildconnection(ip_str)

    if not ok:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "message": "Verbindung zur Drohne fehlgeschlagen"
            }
        )

    return {
        "status": "ok",
        "message": f"Drohne erfolgreich verbunden ({ip_str})",
        "restarting": False
    }


@router.post("/disconnect")
def disconnect_drone():
    if not drohne_service.is_connected():
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Keine Drohne verbunden"
            }
        )

    drohne_service.close()
    return {
        "status": "ok",
        "message": "Drohne wurde getrennt"
    }

@router.websocket("/telemetrie")
async def gettelemetrie(ws: WebSocket):
    await ws.accept()
    print("[WebSocket] Telemetrie verbunden")

    try:
        while True:
            data = telemtrie_service.get_telemetry()
            await ws.send_json(data)
            await asyncio.sleep(0.1)  # alle 500 ms aktualisieren

    except WebSocketDisconnect:
        print("[WebSocket] Telemetrie getrennt")

    except Exception as e:
        print(f"[WebSocket] Fehler: {e}")
        try:
            await ws.close()
        except Exception:
            pass

@router.post("/save-flight-name")
async def save_flight_name(req: FlightRequest):
    """Speichert den letzten Flug aus dem telemtrieService Puffer."""
    s, e = telemtrie_service.last_completed_flight["start"], telemtrie_service.last_completed_flight["end"]
    if s and e:
        label_flight(s - timedelta(seconds=5), e + timedelta(seconds=1), req.name)
        telemtrie_service.last_completed_flight = {"start": None, "end": None}
        return {"ok": True}
    return {"ok": False, "message": "Kein Flug im Puffer"}

@router.get("/flights")
async def list_flights():
    return {"ok": True, "flights": get_all_flight_names()}

@router.get("/flights")
async def list_flights(): return {"ok": True, "flights": get_all_flight_names()}

from typing import List
from fastapi import Body

from fastapi import Body

@router.post("/led")
async def send_led_image(data: dict = Body(...)):
    matrix_str = data.get("matrix")

    print("LED STRING:", matrix_str)

    ok = telemtrie_service.set_matrix_string(matrix_str)

    if not ok:
        return {
            "status": "error",
            "message": "Bild konnte nicht angezeigt werden"
        }

    return {
        "status": "ok",
        "mode": "image"
    }

@router.post("/command")
async def send_led_text(data: dict = Body(...)):
    command = data.get("command")
    color = data.get("color", "r")

    print("COMMAND:", command)
    print("COLOR:", color)

    ok = telemtrie_service.set_matrix_text(command, color=color, scroll=True)

    if not ok:
        return {
            "status": "error",
            "message": "Text konnte nicht angezeigt werden"
        }

    return {
        "status": "ok",
        "mode": "text-scroll",
        "command": command,
        "color": color
    }