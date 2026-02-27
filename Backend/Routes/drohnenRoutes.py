from fastapi import APIRouter, Body, HTTPException
import ipaddress

import Services.drohneService as drohne_service
import Services.drohneService as ds

router = APIRouter()

@router.post("/connect")
def connect_drone(ip: str = Body(..., embed=True)):

    # 1) IPv4 validieren
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

    # 2) Verbindung aufbauen
    ok = drohne_service.buildconnection(str(ip_obj))

    if not ok:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Verbindung zur Drohne fehlgeschlagen"
            }
        )

    # 3) Erfolg
    return {
        "status": "ok",
        "message": f"Drohne erfolgreich verbunden ({ip_obj})"
    }

@router.post("/disconnect")
def disconnect_drone():
    if(ds.ep_drone is None):
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message" : "Keine Drohne Verbunden"
            }
        )

    drohne_service.close()
    return {
        "status": "ok",
    }



