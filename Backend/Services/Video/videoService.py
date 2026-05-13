from __future__ import annotations

import threading
import cv2
import os
import uuid
from Models.video import Video
from sqlmodel import Session
from connect import engine


class VideoService:
    def __init__(self):
        self.writer = None
        self.is_recording = False
        self.output_dir = "data/videos"
        self.current_filename = None

        # Thread-Synchronisation
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.frame_available = threading.Event()
        self.worker_thread: threading.Thread | None = None

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def start_recording(self, width=640, height=480, fps=20.0):
        if self.is_recording:
            return

        self.current_filename = f"rec_{uuid.uuid4().hex}.mp4"
        path = os.path.join(self.output_dir, self.current_filename)

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
        self.is_recording = True

        # Alten State zurücksetzen
        with self.frame_lock:
            self.latest_frame = None
        self.frame_available.clear()

        # EIN Worker-Thread für das Schreiben
        self.worker_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self.worker_thread.start()

        print(f"[Recorder] Start: {self.current_filename}")

    def write_frame(self, frame):
        """Vom Stream-Loop aufgerufen. Nicht-blockierend: legt nur den Frame ab."""
        if not self.is_recording:
            return

        with self.frame_lock:
            # .copy() verhindert, dass der Writer-Thread auf einem Frame schreibt,
            # den der Stream-Loop nebenbei schon weiterverarbeitet
            self.latest_frame = frame.copy()
        self.frame_available.set()

    def _writer_loop(self):
        """Läuft im Hintergrund. Schreibt Frames sequenziell in die Datei."""
        while self.is_recording:
            # Warten bis ein neuer Frame da ist (max. 0.5s, damit wir Stop mitkriegen)
            if not self.frame_available.wait(timeout=0.5):
                continue

            with self.frame_lock:
                frame = self.latest_frame
                self.latest_frame = None
                self.frame_available.clear()

            if frame is None:
                continue

            try:
                if self.writer is not None:
                    self.writer.write(frame)
            except Exception as e:
                print(f"Fehler beim Schreiben des Frames: {e}")

    def stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        # Worker aufwecken, damit er die Schleife verlässt
        self.frame_available.set()

        if self.worker_thread is not None:
            self.worker_thread.join(timeout=5.0)
            self.worker_thread = None

        if self.writer:
            self.writer.release()
            self.writer = None

        with Session(engine) as session:
            new_video = Video(filename=self.current_filename)
            session.add(new_video)
            session.commit()

        print(f"[Recorder] Gespeichert in DB und File: {self.current_filename}")


video_service = VideoService()