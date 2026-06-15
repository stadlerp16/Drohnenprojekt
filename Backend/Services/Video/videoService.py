from __future__ import annotations

import threading
import time
import cv2
import os
import uuid
from Models.video import Video
from sqlmodel import Session
from connect import engine
import subprocess
import imageio_ffmpeg

FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()


class VideoService:
    def __init__(self):
        self.writer = None
        self.is_recording = False
        self.output_dir = "data/videos"
        self.current_filename = None
        self.current_path = None

        self.frames_written = 0
        self.recording_start_time: float | None = None
        self.width = None
        self.height = None

        # Thread-Synchronisation
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.frame_available = threading.Event()
        self.worker_thread: threading.Thread | None = None

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def start_recording(self, width=640, height=480):
        if self.is_recording:
            return

        self.current_filename = f"rec_{uuid.uuid4().hex}.mp4"
        self.current_path = os.path.join(self.output_dir, self.current_filename)
        self.width = width
        self.height = height

        # Provisorische FPS - wird beim Stop durch reale FPS ersetzt
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(self.current_path, fourcc, 30.0, (width, height))

        self.is_recording = True
        self.frames_written = 0
        self.recording_start_time = time.time()

        with self.frame_lock:
            self.latest_frame = None
        self.frame_available.clear()

        self.worker_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self.worker_thread.start()

        print(f"[Recorder] Start: {self.current_filename}")

    def write_frame(self, frame):
        if not self.is_recording:
            return

        with self.frame_lock:
            self.latest_frame = frame.copy()
        self.frame_available.set()

    def _writer_loop(self):
        while self.is_recording:
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
                    self.frames_written += 1
            except Exception as e:
                print(f"Fehler beim Schreiben des Frames: {e}")

    def stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        self.frame_available.set()

        if self.worker_thread is not None:
            self.worker_thread.join(timeout=5.0)
            self.worker_thread = None

        # Echte FPS aus tatsächlicher Aufnahme berechnen
        duration = time.time() - self.recording_start_time
        real_fps = self.frames_written / duration if duration > 0 else 30.0
        print(f"[Recorder] Stop: written={self.frames_written}, "
              f"dauer={duration:.1f}s, real_fps={real_fps:.2f}")

        if self.writer:
            self.writer.release()
            self.writer = None

        if self.frames_written == 0:
            print(f"[Recorder] ⚠️  Keine Frames, kein DB-Eintrag")
            return

        # Datei mit korrekter FPS neu schreiben
        self._rewrite_with_correct_fps(real_fps)

        with Session(engine) as session:
            new_video = Video(filename=self.current_filename)
            session.add(new_video)
            session.commit()

        print(f"[Recorder] Gespeichert in DB und File: {self.current_filename}")

    def _rewrite_with_correct_fps(self, real_fps: float):
        """
        Re-encodet die Datei mit ffmpeg zu browserkompatiblem H.264:
        - libx264 Codec (browserkompatibel, im Gegensatz zu mp4v)
        - yuv420p Pixel-Format (zwingend für Browser)
        - +faststart (moov atom am Anfang -> Streaming statt voller Download)
        - Korrekte FPS aus tatsächlicher Aufnahmerate
        """
        tmp_path = self.current_path + ".tmp.mp4"

        try:
            result = subprocess.run(
                [
                    FFMPEG_BIN, "-y",
                    "-r", str(real_fps),
                    "-i", self.current_path,
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-crf", "23",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    tmp_path,
                ],
                check=True,
                capture_output=True,
            )

            os.replace(tmp_path, self.current_path)
            print(f"[Recorder] Re-encoded H.264 @ {real_fps:.2f} FPS (browserkompatibel)")

        except subprocess.CalledProcessError as e:
            print(f"[Recorder]fmpeg-Konvertierung fehlgeschlagen:")
            print(e.stderr.decode(errors='ignore')[:500])
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception as e:
            print(f"[Recorder] Unerwarteter Fehler: {e}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

video_service = VideoService()