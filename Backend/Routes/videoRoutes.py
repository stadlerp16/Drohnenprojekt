from fastapi import APIRouter, WebSocket
from Services.Video.liveStream import  video_stream_service


router = APIRouter()


@router.websocket("/getlivestream")
async def websocket_video_stream(websocket: WebSocket):
    await video_stream_service.stream_to_websocket(websocket)