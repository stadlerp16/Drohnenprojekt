from fastapi import APIRouter, Body, HTTPException
import ipaddress

import Services.drohneService as drohne_service


router = APIRouter()

@router.post("/connect")
def connect_drone(ip: str = Body(..., embed=True)):
    # Erwarteter Body:
    # { "ip": "192.168.0.10" }

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

    # 2) Service aufrufen (Implementierung später)
    drohne_service.buildconnection(str(ip_obj))

    # 3) Erfolgsmeldung
    return {
        "status": "ok",
        "message": f"Verbindungsaufbau zur Drohne mit IPv4-Adresse {ip_obj} gestartet."
    }
