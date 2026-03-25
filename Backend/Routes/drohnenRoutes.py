import asyncio

from fastapi import APIRouter, Body, HTTPException
import ipaddress

from starlette.websockets import WebSocketDisconnect

from starlette.websockets import WebSocket

import Services.DrohneVerwaltung.drohneService as drohne_service
import Services.DrohneVerwaltung.telemtrieService as telemtrie_service
from connect import get_all_flight_names

router = APIRouter()


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
            await asyncio.sleep(0.5)  # alle 500 ms aktualisieren

    except WebSocketDisconnect:
        print("[WebSocket] Telemetrie getrennt")

    except Exception as e:
        print(f"[WebSocket] Fehler: {e}")
        try:
            await ws.close()
        except Exception:
            pass

@router.get("/flights")
async def list_flights(): return {"ok": True, "flights": get_all_flight_names()}