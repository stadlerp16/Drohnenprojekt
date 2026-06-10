from fastapi import APIRouter, WebSocket, HTTPException, Body
from Services.Video.liveStream import  video_stream_service
import Services.DrohneVerwaltung.drohneService as drohne_service
import Services.Video.liveStream as livestream
from fastapi import APIRouter, WebSocket, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from sqlmodel import Session, select
import os
import re
from Models.video import Video
from connect import engine


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



@router.post("/start")
async def start_rec():
    video_stream_service.start_recording()
    return {"status": "recording started"}


@router.post("/stop")
async def stop_rec():
    video_stream_service.stop_recording()
    return {"status": "recording stopped"}


@router.get("/list")
async def list_videos():
    """
    Liefert alle Aufnahmen aus der DB, sortiert nach Datum (neueste zuerst).
    Dateien, die nicht mehr im Dateisystem existieren, werden gefiltert.
    """
    videos = []

    try:
        with Session(engine) as session:
            statement = select(Video).order_by(Video.created_at.desc())
            results = session.exec(statement).all()

            for video in results:
                file_path = os.path.join(video_service.output_dir, video.filename)
                if not os.path.exists(file_path):
                    continue

                videos.append({
                    "id": video.id,
                    "filename": video.filename,
                    "created_at": video.created_at.isoformat() if video.created_at else None,
                    "size_bytes": os.path.getsize(file_path),
                    "url": f"/file/{video.filename}",
                })
    except Exception as e:
        print(f"[Video List] DB-Fehler: {e}")

    return {"videos": videos}


@router.get("/file/{filename}")
async def get_video_file(filename: str, request: Request):
    """
    Liefert ein Video mit HTTP-Range-Support, damit Browser
    das Video sauber abspielen und spulen können.
    """
    safe_filename = os.path.basename(filename)
    if safe_filename != filename:
        raise HTTPException(status_code=400, detail="Ungültiger Dateiname")

    file_path = os.path.join(video_service.output_dir, safe_filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video nicht gefunden")

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")

    # Kein Range-Header -> komplette Datei zurück
    if range_header is None:
        return FileResponse(
            path=file_path,
            media_type="video/mp4",
            headers={"Accept-Ranges": "bytes"},
        )

    # Range parsen: "bytes=0-1023" oder "bytes=1024-"
    range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
    if not range_match:
        raise HTTPException(status_code=400, detail="Ungültiger Range-Header")

    start = int(range_match.group(1))
    end_str = range_match.group(2)
    end = int(end_str) if end_str else file_size - 1

    if start >= file_size or end >= file_size:
        raise HTTPException(
            status_code=416,
            detail="Range nicht erfüllbar",
            headers={"Content-Range": f"bytes */{file_size}"}
        )

    chunk_size = end - start + 1

    def iter_file():
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = chunk_size
            while remaining > 0:
                read_size = min(1024 * 1024, remaining)
                data = f.read(read_size)
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_size),
        "Content-Type": "video/mp4",
    }

    return StreamingResponse(
        iter_file(),
        status_code=206,
        headers=headers,
        media_type="video/mp4",
    )


@router.delete("/file/{filename}")
async def delete_video(filename: str):
    safe_filename = os.path.basename(filename)
    if safe_filename != filename:
        raise HTTPException(status_code=400, detail="Ungültiger Dateiname")

    file_path = os.path.join(video_service.output_dir, safe_filename)

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Datei konnte nicht gelöscht werden: {e}"
            )

    try:
        with Session(engine) as session:
            statement = select(Video).where(Video.filename == safe_filename)
            video = session.exec(statement).first()
            if video:
                session.delete(video)
                session.commit()
    except Exception as e:
        print(f"[Video Delete] DB-Fehler: {e}")

    return {"status": "deleted", "filename": safe_filename}
