from fastapi import APIRouter, WebSocket, HTTPException, Body
from Services.Video.liveStream import  video_stream_service
import Services.DrohneVerwaltung.drohneService as drohne_service
import Services.Video.liveStream as livestream

router = APIRouter()


@router.websocket("/getlivestream")
async def websocket_video_stream(websocket: WebSocket):
    await websocket.accept()
    if drohne_service.ep_drone is None:
        livestream.logger.warning(f"[Conn Keine Drohne verbunden")
        await websocket.send_json({"type": "error", "message": "Keine Drohne verbunden"})
        await websocket.close()
        return
    await video_stream_service.stream_to_websocket(websocket)

@router.post("/enableObject")
async def websocket_video_stream_enable(enable: bool = Body(..., embed=True)):
    # Drohne nur prüfen, NICHT mehr die Zuweisung daran hängen
    if drohne_service.ep_drone is None and not drohne_service.is_connected():
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": "Keine Drohne verbunden"},
        )

    livestream.object_detection_enabled = enable
    return {
        "status": "ok",
        "message": f"Object detection {'enabled' if enable else 'disabled'}",
        "object_detection_enabled": enable,
    }
