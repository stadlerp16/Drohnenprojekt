import cv2
import base64
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
import Services.DrohneVerwaltung.drohneService as drohneService


class VideoStreamService:
    def __init__(self):
        self.running = False

    async def stream_to_websocket(self, websocket: WebSocket):
        await websocket.accept()

        if drohneService.ep_drone is None:
            await websocket.send_json({
                "type": "error",
                "message": "Keine Drohne verbunden"
            })
            await websocket.close()
            return

        try:
            self.running = True
            drohneService.ep_drone.camera.start_video_stream(display=False)

            while self.running:
                frame = drohneService.ep_drone.camera.read_cv2_image(strategy="newest")

                if frame is None:
                    await asyncio.sleep(0.03)
                    continue

                frame = cv2.resize(frame, (640, 480))

                success, buffer = cv2.imencode(".jpg", frame)
                if not success:
                    await asyncio.sleep(0.03)
                    continue

                frame_base64 = base64.b64encode(buffer).decode("utf-8")

                await websocket.send_json({
                    "type": "video_frame",
                    "image": frame_base64
                })

                await asyncio.sleep(0.03)

        except WebSocketDisconnect:
            pass

        except Exception as e:
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Videostream-Fehler: {str(e)}"
                })
            except:
                pass

        finally:
            self.running = False
            try:
                if drohneService.ep_drone is not None:
                    drohneService.ep_drone.camera.stop_video_stream()
            except:
                pass


video_stream_service = VideoStreamService()