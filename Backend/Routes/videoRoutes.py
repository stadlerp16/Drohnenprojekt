from fastapi import APIRouter, WebSocket
from Services.Video.liveStream import  video_stream_service
from Services.Video.videoService import video_service

router = APIRouter()


@router.websocket("/getlivestream")
async def websocket_video_stream(websocket: WebSocket):
    await video_stream_service.stream_to_websocket(websocket)

@router.post("/start")
async def start_rec():
    video_service.start_recording()
    return {"status": "recording started"}

@router.post("/stop")
async def stop_rec():
    video_service.stop_recording()
    return {"status": "recording stopped"}