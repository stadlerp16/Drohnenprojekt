import threading

import cv2
import os
import uuid
from Models.video import Video
# IMPORT KORREKTUR: Wir brauchen Session und die engine von deiner connect.py
from sqlmodel import Session
from connect import engine


class VideoService:
    def __init__(self):
        self.writer = None
        self.is_recording = False
        self.output_dir = "data/videos"
        self.current_filename = None

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def start_recording(self, width=640, height=480, fps=20.0):
        if self.is_recording: return

        self.current_filename = f"rec_{uuid.uuid4().hex}.mp4"
        path = os.path.join(self.output_dir, self.current_filename)

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
        self.is_recording = True
        print(f"[Recorder] Start: {self.current_filename}")

    def write_frame(self, frame):
        if self.is_recording and self.writer:
            thread = threading.Thread(target=self._sync_write, args=(frame,))
            thread.start()

    def _sync_write(self, frame):
        """Die eigentliche (langsame) Schreib-Operation"""
        try:
            self.writer.write(frame)
        except Exception as e:
            print(f"Fehler beim Schreiben des Frames: {e}")

    def stop_recording(self):
        if not self.is_recording: return

        self.is_recording = False
        if self.writer:
            self.writer.release()
            self.writer = None

        # SQLModel Weg: Wir nutzen die engine direkt in einem Context-Manager
        with Session(engine) as session:
            new_video = Video(filename=self.current_filename)
            session.add(new_video)
            session.commit()
            # session.refresh(new_video) # Nicht zwingend nötig, wenn wir danach printen

        print(f"[Recorder] Gespeichert in DB und File: {self.current_filename}")


video_service = VideoService()