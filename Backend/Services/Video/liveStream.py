import cv2
import base64
import asyncio
import logging
from queue import Empty
from fastapi import WebSocket, WebSocketDisconnect
from ultralytics import YOLO
import Services.DrohneVerwaltung.drohneService as drohneService
from Services.Video.videoService import video_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("VideoStream")


class VideoStreamService:
    def __init__(self):
        self.running = False
        self.frame_count = 0
        self.last_detections = []
        self.model = YOLO("yolov8n.pt")
        self._lock = asyncio.Lock()
        self._connection_count = 0
        self._stream_started = False
        logger.info("VideoStreamService initialisiert")

    def _ensure_stream_started(self):
        """Startet den Kamerastream einmalig, falls noch nicht aktiv"""
        if self._stream_started:
            return True

        if drohneService.ep_drone is None:
            logger.error("Keine Drohne verbunden - Stream kann nicht gestartet werden")
            return False

        try:
            drohneService.ep_drone.camera.start_video_stream(display=False)
            self._stream_started = True
            logger.info("Kamerastream gestartet (persistent)")
            return True
        except Exception as e:
            logger.error(f"Stream-Start fehlgeschlagen: {e}")
            return False

    def dispose(self):
        """
        Wird beim Drohnen-Disconnect/close() aufgerufen.
        Stoppt aktive WebSocket-Loops und schließt den Kamerastream sauber.
        """
        logger.info("dispose() aufgerufen")

        # Aktive WebSocket-Loops beenden
        self.running = False

        # Kamerastream stoppen - nur wenn die Drohne noch existiert
        if self._stream_started:
            try:
                if drohneService.ep_drone is not None:
                    drohneService.ep_drone.camera.stop_video_stream()
                    logger.info("Kamerastream gestoppt")
            except Exception as e:
                logger.error(f"Fehler beim stop_video_stream: {e}")
            finally:
                self._stream_started = False

        # State zurücksetzen
        self.frame_count = 0
        self.last_detections = []
        logger.info("dispose() fertig")

    async def stream_to_websocket(self, websocket: WebSocket, object_detection_enabled: bool = True):
        self._connection_count += 1
        conn_id = self._connection_count
        logger.info(f"[Conn #{conn_id}] WebSocket-Verbindung wird akzeptiert")

        await websocket.accept()

        if drohneService.ep_drone is None:
            logger.warning(f"[Conn #{conn_id}] Keine Drohne verbunden")
            await websocket.send_json({"type": "error", "message": "Keine Drohne verbunden"})
            await websocket.close()
            return

        # Falls noch ein alter WebSocket-Loop läuft, erst stoppen lassen
        if self.running:
            logger.warning(f"[Conn #{conn_id}] Alter WebSocket-Loop läuft - stoppe ihn")
            self.running = False
            await asyncio.sleep(0.2)

        async with self._lock:
            logger.info(f"[Conn #{conn_id}] Lock acquired")
            empty_counter = 0
            frames_sent = 0

            try:
                self.running = True
                self.frame_count = 0
                self.last_detections = []

                # Stream nur starten falls noch nicht aktiv
                if not self._ensure_stream_started():
                    await websocket.send_json({
                        "type": "error",
                        "message": "Stream konnte nicht gestartet werden"
                    })
                    return

                logger.info(f"[Conn #{conn_id}] Betrete Frame-Loop")

                while self.running:
                    # Frame holen - mit Exception-Handling für Empty queue
                    frame = None
                    try:
                        frame = await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: drohneService.ep_drone.camera.read_cv2_image(
                                strategy="newest", timeout=1.0
                            )
                        )
                    except Empty:
                        empty_counter += 1
                        if empty_counter % 5 == 0:
                            logger.warning(
                                f"[Conn #{conn_id}] Queue Empty {empty_counter}x in Folge"
                            )
                        if empty_counter >= 30:
                            logger.error(
                                f"[Conn #{conn_id}] Drohne sendet keine Frames - breche ab"
                            )
                            try:
                                await websocket.send_json({
                                    "type": "error",
                                    "message": "Keine Frames von Drohne"
                                })
                            except:
                                pass
                            break
                        await asyncio.sleep(0.1)
                        continue
                    except Exception as e:
                        logger.error(f"[Conn #{conn_id}] Fehler beim Frame lesen: {e}")
                        await asyncio.sleep(0.1)
                        continue

                    if frame is None:
                        empty_counter += 1
                        await asyncio.sleep(0.03)
                        continue

                    if empty_counter > 0:
                        logger.info(f"[Conn #{conn_id}] Frame nach {empty_counter} leeren erhalten")
                        empty_counter = 0

                    video_service.write_frame(frame)

                    frame = cv2.resize(frame, (640, 480))

                    # Objekterkennung
                    detections = []
                    detections_changed = False

                    if object_detection_enabled and self.frame_count % 4 == 0:
                        results = self.model(frame, conf=0.5)
                        detections = self._extract_detections(results[0])
                        detections = self._get_closest_object(detections)
                        detections_changed = self._detections_changed(detections)

                        if detections_changed:
                            self.last_detections = detections
                        else:
                            detections = self.last_detections
                    else:
                        detections = self.last_detections

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

                    frames_sent += 1
                    if frames_sent == 1:
                        logger.info(f"[Conn #{conn_id}] ERSTER Frame gesendet!")
                    elif frames_sent % 100 == 0:
                        logger.info(f"[Conn #{conn_id}] {frames_sent} Frames gesendet")

                    self.frame_count += 1
                    await asyncio.sleep(0.03)

                logger.info(f"[Conn #{conn_id}] Loop beendet (running={self.running})")

            except WebSocketDisconnect:
                logger.info(f"[Conn #{conn_id}] WebSocket disconnected")

            except Exception as e:
                logger.exception(f"[Conn #{conn_id}] Unerwarteter Fehler")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Videostream-Fehler: {str(e)}"
                    })
                except:
                    pass

            finally:
                logger.info(
                    f"[Conn #{conn_id}] Cleanup - frames_sent={frames_sent}, "
                    f"empty_counter={empty_counter}"
                )
                self.running = False
                # WICHTIG: Stream NICHT stoppen - bleibt für nächste Verbindung aktiv!
                # Stream wird erst in dispose() (beim Drohnen-close) gestoppt
                logger.info(f"[Conn #{conn_id}] Cleanup fertig (Stream läuft weiter)")

    def _extract_detections(self, results):
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
        if len(detections) == 0:
            return []
        if len(detections) == 1:
            return detections

        detections_with_area = []
        for det in detections:
            bbox = det["bbox"]
            area = (bbox["x2"] - bbox["x1"]) * (bbox["y2"] - bbox["y1"])
            detections_with_area.append((det, area))

        detections_with_area.sort(key=lambda x: x[1], reverse=True)
        return [detections_with_area[0][0]]

    def _detections_changed(self, current_detections):
        if len(current_detections) != len(self.last_detections):
            return True
        if len(current_detections) == 0:
            return False

        curr = current_detections[0]
        last = self.last_detections[0]

        if curr["class"] != last["class"]:
            return True
        if abs(curr["confidence"] - last["confidence"]) > 0.05:
            return True

        bbox_curr = curr["bbox"]
        bbox_last = last["bbox"]
        x_diff = abs(bbox_curr["x1"] - bbox_last["x1"])
        y_diff = abs(bbox_curr["y1"] - bbox_last["y1"])

        if x_diff > 30 or y_diff > 30:
            return True

        return False


video_stream_service = VideoStreamService()
