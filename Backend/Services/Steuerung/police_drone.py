import asyncio
import time
import logging
from Services.Steuerung.flightExekutor import set_rc
import Services.Video.liveStream as liveStream
import Services.DrohneVerwaltung.drohneService as drohneService

logger = logging.getLogger("PoliceDrone")

# Bildauflösung (muss zu liveStream cv2.resize passen!)
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FRAME_CENTER_X = FRAME_WIDTH / 2
FRAME_CENTER_Y = FRAME_HEIGHT / 2

# Ziel-Größe der Bounding-Box (steuert Distanz zur Person)
# Größere Box = Person näher dran
TARGET_BOX_AREA_RATIO = 0.25  # Person soll ~15% des Bildes einnehmen
AREA_TOLERANCE = 0.04  # ±5% Toleranz, damit Drohne nicht ständig korrigiert

# Maximale RC-Werte (wie deine anderen Modi)
MAX_SPEED = 40

# Proportional-Regler Konstanten (vorsichtig starten!)
# Je höher, desto aggressiver die Korrektur
KP_YAW = 0.15  # Yaw-Drehung um Person zu zentrieren (x-Achse)
KP_THROTTLE = 0.15  # Höhe um Person vertikal zu zentrieren (y-Achse)
KP_FORWARD = 250  # Vorwärts/Rückwärts um Distanz zu halten

# Toleranz im Pixel - innerhalb dieser Zone wird nicht korrigiert
CENTER_TOLERANCE_X = 50  # Pixel
CENTER_TOLERANCE_Y = 40  # Pixel

# Such-Verhalten wenn Person verloren
SEARCH_YAW_SPEED = 30  # Im Kreis drehen mit dieser Geschwindigkeit
LOST_GRACE_PERIOD = 1.0  # Sekunden warten bevor Suche startet

# Update-Rate
UPDATE_HZ = 15


class PoliceDroneMode:
    def __init__(self):
        self.active = False
        self._task = None
        self._stop_event = asyncio.Event()
        self._person_lost_since = None
        logger.info("PoliceDroneMode initialisiert")

    def is_active(self) -> bool:
        return self.active

    async def start(self) -> bool:
        drohneService.ep_drone.led.set_led_blink(freq=1, r1=255, g1=0, b1=0, r2=0, g2=0, b2=255)

        """Startet den Tracking-Modus"""
        if self.active:
            logger.warning("Tracking läuft bereits")
            return False

        if drohneService.ep_drone is None:
            logger.error("Keine Drohne verbunden")
            return False

        self.active = True
        self._stop_event.clear()
        self._person_lost_since = None
        self._task = asyncio.create_task(self._tracking_loop())
        logger.info("Person-Tracking gestartet")
        return True

    async def stop(self) -> bool:
        """Stoppt den Tracking-Modus"""
        if not self.active:
            return False

        logger.info("Person-Tracking wird gestoppt")
        self.active = False
        self._stop_event.set()

        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=2.0)
            except asyncio.TimeoutError:
                logger.warning("Tracking-Task Timeout beim Stoppen")
            self._task = None

        # Wichtig: RC auf 0 setzen damit Drohne stehen bleibt
        set_rc(0, 0, 0, 0)
        logger.info("Person-Tracking gestoppt")
        return True

    async def _tracking_loop(self):
        """Hauptschleife - läuft mit UPDATE_HZ"""
        dt = 1.0 / UPDATE_HZ
        logger.info(f"Tracking-Loop gestartet ({UPDATE_HZ} Hz)")

        try:
            while not self._stop_event.is_set():
                detection = liveStream.video_stream_service.get_latest_person_detection()

                if detection is None:
                    self._handle_person_lost()
                else:
                    self._handle_person_detected(detection)

                await asyncio.sleep(dt)
        except Exception as e:
            logger.exception(f"Fehler im Tracking-Loop: {e}")
        finally:
            # Sicherheits-Stop
            set_rc(0, 0, 0, 0)
            logger.info("Tracking-Loop beendet")

    def _handle_person_detected(self, detection):
        """Person wurde erkannt - berechne RC-Werte"""
        self._person_lost_since = None  # Reset Lost-Timer

        bbox = detection["bbox"]

        # Bounding-Box Mitte
        box_center_x = (bbox["x1"] + bbox["x2"]) / 2
        box_center_y = (bbox["y1"] + bbox["y2"]) / 2

        # Bounding-Box Fläche (für Distanz-Schätzung)
        box_width = bbox["x2"] - bbox["x1"]
        box_height = bbox["y2"] - bbox["y1"]
        box_area = box_width * box_height
        frame_area = FRAME_WIDTH * FRAME_HEIGHT
        area_ratio = box_area / frame_area

        # Fehler berechnen (wieviel weicht die Person vom Ziel ab)
        error_x = box_center_x - FRAME_CENTER_X  # positiv = Person rechts
        error_y = box_center_y - FRAME_CENTER_Y  # positiv = Person unten
        error_area = TARGET_BOX_AREA_RATIO - area_ratio  # positiv = Person zu klein/weit weg

        # YAW: Drohne dreht sich um Person horizontal zu zentrieren
        if abs(error_x) > CENTER_TOLERANCE_X:
            yaw = int(error_x * KP_YAW)
        else:
            yaw = 0

        # THROTTLE: Drohne steigt/sinkt um Person vertikal zu zentrieren
        # Achtung: y-Achse ist invertiert (oben = kleines y)
        if abs(error_y) > CENTER_TOLERANCE_Y:
            throttle = int(-error_y * KP_THROTTLE)  # Minus weil Drohne nach oben fliegen soll wenn Person oben ist
        else:
            throttle = 0

        # FORWARD: Drohne fliegt vor/zurück um Distanz zu halten
        if abs(error_area) > AREA_TOLERANCE:
            forward = int(error_area * KP_FORWARD)
        else:
            forward = 0

        # Auf MAX_SPEED begrenzen
        yaw = max(-MAX_SPEED, min(MAX_SPEED, yaw))
        throttle = max(-MAX_SPEED, min(MAX_SPEED, throttle))
        forward = max(-MAX_SPEED, min(MAX_SPEED, forward))

        # RC setzen: a=strafe(0), b=forward, c=up/down, d=yaw
        set_rc(a=0, b=forward, c=throttle, d=yaw)

    def _handle_person_lost(self):
        """Keine Person sichtbar - im Kreis drehen zur Suche"""
        now = time.time()

        if self._person_lost_since is None:
            self._person_lost_since = now

        # Erste Sekunde nur stehenbleiben (vielleicht kommt Person gleich wieder)
        if now - self._person_lost_since < LOST_GRACE_PERIOD:
            set_rc(a=0, b=0, c=0, d=0)
            return

        # Im Kreis drehen bis Person wieder gefunden
        set_rc(a=0, b=0, c=0, d=SEARCH_YAW_SPEED)


# Singleton
police_drone_mode = PoliceDroneMode()