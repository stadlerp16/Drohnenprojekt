import cv2
import base64
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from ultralytics import YOLO
import Services.DrohneVerwaltung.drohneService as drohneService


class VideoStreamService:
    def __init__(self):
        self.running = False
        self.frame_count = 0
        self.last_detections = []  # Speichert letzte Detektionen
        # YOLO-Modell laden (einmalig beim Init)
        self.model = YOLO("yolov8n.pt")  # nano-Version für schnellere Inference

    async def stream_to_websocket(self, websocket: WebSocket, object_detection_enabled: bool = True):
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
            self.frame_count = 0
            self.last_detections = []
            drohneService.ep_drone.camera.start_video_stream(display=False)

            while self.running:
                frame = drohneService.ep_drone.camera.read_cv2_image(strategy="newest")

                if frame is None:
                    await asyncio.sleep(0.03)
                    continue

                frame = cv2.resize(frame, (640, 480))

                # Objekterkennung nur durchführen bei jedem 4. Frame
                detections = []
                detections_changed = False

                if object_detection_enabled and self.frame_count % 4 == 0:
                    results = self.model(frame, conf=0.5)
                    detections = self._extract_detections(results[0])

                    # Nur das nächste Objekt (größte Bounding Box) behalten
                    detections = self._get_closest_object(detections)

                    # Prüfe ob sich Detektionen geändert haben
                    detections_changed = self._detections_changed(detections)

                    if detections_changed:
                        self.last_detections = detections
                    else:
                        # Wenn nichts geändert hat, alte Detektionen weiterverwenden
                        detections = self.last_detections
                else:
                    # Wenn nicht erkannt wird, letzte Detektionen weiterverwenden
                    detections = self.last_detections

                # Frame in Base64 kodieren (OHNE Rechteck-Zeichnung)
                success, buffer = cv2.imencode(".jpg", frame)
                if not success:
                    await asyncio.sleep(0.03)
                    self.frame_count += 1
                    continue

                frame_base64 = base64.b64encode(buffer).decode("utf-8")

                await websocket.send_json({
                    "type": "video_frame",
                    "image": frame_base64,
                    "object_detection_enabled": object_detection_enabled,
                    "detections": detections,
                    "detections_changed": detections_changed
                })

                self.frame_count += 1
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

    def _extract_detections(self, results):
        """Extrahiert erkannte Objekte als strukturierte Daten"""
        detections = []

        if results.boxes is not None:
            for box in results.boxes:
                detection = {
                    "class": results.names[int(box.cls)],
                    "confidence": float(box.conf),
                    "bbox": {
                        "x1": float(box.xyxy[0][0]),
                        "y1": float(box.xyxy[0][1]),
                        "x2": float(box.xyxy[0][2]),
                        "y2": float(box.xyxy[0][3])
                    }
                }
                detections.append(detection)

        return detections

    def _get_closest_object(self, detections):
        """
        Behält nur das nächste Objekt (größte Bounding Box).
        Größere Box = näher an der Kamera
        """
        if len(detections) == 0:
            return []

        if len(detections) == 1:
            return detections

        # Berechne Fläche jeder Bounding Box
        detections_with_area = []
        for det in detections:
            bbox = det["bbox"]
            area = (bbox["x2"] - bbox["x1"]) * (bbox["y2"] - bbox["y1"])
            detections_with_area.append((det, area))

        # Sortiere nach Fläche (absteigend) und behalte nur das größte
        detections_with_area.sort(key=lambda x: x[1], reverse=True)
        return [detections_with_area[0][0]]

    def _detections_changed(self, current_detections):
        """
        Prüft ob sich die Detektionen signifikant geändert haben.
        Ignoriert kleine Positionsänderungen.
        """
        # Wenn Anzahl der Objekte unterschiedlich ist
        if len(current_detections) != len(self.last_detections):
            return True

        # Wenn keine Objekte
        if len(current_detections) == 0:
            return False

        # Prüfe ob Klasse oder Confidence sich geändert haben
        curr = current_detections[0]
        last = self.last_detections[0]

        # Unterschiedliche Klasse
        if curr["class"] != last["class"]:
            return True

        # Confidence Unterschied > 5%
        if abs(curr["confidence"] - last["confidence"]) > 0.05:
            return True

        # Position Unterschied > 30 Pixel (größere Toleranz)
        bbox_curr = curr["bbox"]
        bbox_last = last["bbox"]

        x_diff = abs(bbox_curr["x1"] - bbox_last["x1"])
        y_diff = abs(bbox_curr["y1"] - bbox_last["y1"])

        if x_diff > 30 or y_diff > 30:
            return True

        return False


video_stream_service = VideoStreamService()