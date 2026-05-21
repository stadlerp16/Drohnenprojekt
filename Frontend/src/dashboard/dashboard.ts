import { Component, ElementRef, HostListener, OnDestroy, OnInit, ViewChild, ChangeDetectorRef, NgZone, AfterViewInit } from '@angular/core';
import { DroneService } from '../app/services/drohne.service';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';

interface BBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

interface Detection {
  class: string;
  confidence: number;
  bbox: BBox;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class Dashboard implements OnDestroy, OnInit, AfterViewInit {
  @ViewChild('leftStick') leftStick?: ElementRef;
  @ViewChild('rightStick') rightStick?: ElementRef;
  @ViewChild('leftJoy') leftJoy?: ElementRef;
  @ViewChild('rightJoy') rightJoy?: ElementRef;

  // Canvas-Overlay für Objekterkennung
  @ViewChild('overlayCanvas') overlayCanvas?: ElementRef<HTMLCanvasElement>;

  isFlying: boolean = false;
  isStarted: boolean = false;
  isFlightActive: boolean = false;
  private socket: WebSocket | null = null;
  showSaveModal: boolean = false;
  flightName: string = '';
  showafterland: boolean = false;
  videoStreamSocket: WebSocket | null = null;
  frameData: string = '';

  // OBJEKTERKENNUNG
  // Backend resized Frames auf 640x480 (siehe liveStream.py: cv2.resize(frame, (640, 480)))
  private readonly FRAME_WIDTH = 640;
  private readonly FRAME_HEIGHT = 480;
  currentDetections: Detection[] = [];
  objectDetectionEnabled: boolean = true;

  // RECORDING STATE
  isRecording: boolean = false;
  recordingStartTime: number = 0;
  recordingDuration: string = '00:00';
  private recordingTimerId: any = null;

  // JOYSTICK STATE
  private left = { x: 0, y: 0 };
  private right = { x: 0, y: 0 };
  private draggingSide: 'left' | 'right' | null = null;
  private readonly RADIUS = 50;

  // CONTROLLER KONFIGURATION
  private readonly DEADZONE = 0.08;
  private readonly SEND_HZ = 20;
  private readonly SEND_DT_MS = 1000 / this.SEND_HZ;
  private controllerLoopId: any = null;
  private lastXPressed = false;
  gamepadConnected: boolean = false;
  gamepadName: string = '';

  private readonly allowedKeys = new Set([
    "w", "a", "s", "d", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " ", "Space"
  ]);

  constructor(
    protected droneService: DroneService,
    private router: Router,
    private cdr: ChangeDetectorRef,
    private zone: NgZone
  ) {}

  ngOnInit() {
    this.initVideoStream();
    setTimeout(() => {
      if (this.droneService.isAutoFlight && this.droneService.selectedAutoFlight) {
        this.startAutoFlightFromSetup();
      } else {
        this.connectWebSocket();
      }
    }, 300);
  }

  ngAfterViewInit() {
    // Canvas auf native Frame-Auflösung setzen, damit Bbox-Koordinaten passen
    this.setupCanvas();
  }

  private setupCanvas() {
    if (this.overlayCanvas) {
      const canvas = this.overlayCanvas.nativeElement;
      canvas.width = this.FRAME_WIDTH;
      canvas.height = this.FRAME_HEIGHT;
    }
  }

  private initVideoStream() {
    this.videoStreamSocket = this.droneService.getVideoStreamSocket();

    this.zone.runOutsideAngular(() => {
      if (this.videoStreamSocket) {
        this.videoStreamSocket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            if (data.type === "video_frame") {
              this.frameData = 'data:image/jpeg;base64,' + data.image;

              // Object detection status vom Backend übernehmen
              if (typeof data.object_detection_enabled === 'boolean') {
                this.objectDetectionEnabled = data.object_detection_enabled;
              }

              // Detections verarbeiten (auch leeres Array ist gültig)
              const detections: Detection[] = data.detections || [];
              this.currentDetections = detections;

              this.zone.run(() => {
                // Canvas einrichten falls es erst nach erstem Frame gerendert wird
                if (this.overlayCanvas &&
                  this.overlayCanvas.nativeElement.width !== this.FRAME_WIDTH) {
                  this.setupCanvas();
                }
                this.drawDetections(detections);
                this.cdr.detectChanges();
              });
            }

            if (data.type === "error") {
              console.error("Backend Video Fehler:", data.message);
            }
          } catch (e) {
            console.error("Fehler beim Verarbeiten des Video-Frames:", e);
          }
        };
      }
    });

    if (this.videoStreamSocket) {
      this.videoStreamSocket.onerror = (err) => console.error('Streaming Fehler:', err);
      this.videoStreamSocket.onopen = () => console.log('Video-Stream WebSocket verbunden');
      this.videoStreamSocket.onclose = () => console.log('Video-Stream WebSocket geschlossen');
    }
  }

  // --- OBJEKTERKENNUNG / CANVAS DRAWING ---
  private drawDetections(detections: Detection[]) {
    if (!this.overlayCanvas) return;
    const canvas = this.overlayCanvas.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Canvas immer löschen (auch wenn keine Detections)
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!detections || detections.length === 0) return;

    for (const detection of detections) {
      this.drawDetection(ctx, detection);
    }
  }

  private drawDetection(ctx: CanvasRenderingContext2D, detection: Detection) {
    const bbox = detection.bbox;
    if (!bbox) return;

    const width = bbox.x2 - bbox.x1;
    const height = bbox.y2 - bbox.y1;

    // Grünes Rechteck
    ctx.strokeStyle = '#00ff00';
    ctx.lineWidth = 3;
    ctx.strokeRect(bbox.x1, bbox.y1, width, height);

    // Label
    const label = `${detection.class} ${Math.round(detection.confidence * 100)}%`;
    const fontSize = 18;
    ctx.font = `bold ${fontSize}px Arial`;

    const textMetrics = ctx.measureText(label);
    const textWidth = textMetrics.width;
    const textHeight = fontSize + 8;

    const labelX = bbox.x1;
    let labelY = bbox.y1 - 8;

    // Falls Label oben raus ragt, unterhalb der Bbox platzieren
    if (labelY - fontSize < 0) {
      labelY = bbox.y1 + fontSize + 8;
    }

    // Schwarzer Hintergrund für Text
    ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
    ctx.fillRect(labelX - 4, labelY - fontSize, textWidth + 8, textHeight);

    // Weißer Text
    ctx.fillStyle = '#ffffff';
    ctx.textBaseline = 'top';
    ctx.fillText(label, labelX, labelY - fontSize + 4);
  }

  // --- VIDEO RECORDING ---
  toggleRecording() {
    if (this.isRecording) {
      this.stopRecording();
    } else {
      this.startRecording();
    }
  }

  private startRecording() {
    this.droneService.startRecording().subscribe({
      next: (res) => {
        console.log('Aufnahme gestartet:', res);
        this.isRecording = true;
        this.droneService.isRecording = true;
        this.recordingStartTime = Date.now();
        this.startRecordingTimer();
      },
      error: (err) => console.error('Aufnahme Start Fehler:', err)
    });
  }

  private stopRecording() {
    this.droneService.stopRecording().subscribe({
      next: (res) => {
        console.log('Aufnahme beendet:', res);
        this.isRecording = false;
        this.droneService.isRecording = false;
        this.stopRecordingTimer();
        this.recordingDuration = '00:00';
      },
      error: (err) => console.error('Aufnahme Stop Fehler:', err)
    });
  }

  private startRecordingTimer() {
    this.stopRecordingTimer();
    this.recordingTimerId = setInterval(() => {
      const elapsedMs = Date.now() - this.recordingStartTime;
      const totalSeconds = Math.floor(elapsedMs / 1000);
      const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
      const seconds = (totalSeconds % 60).toString().padStart(2, '0');
      this.recordingDuration = `${minutes}:${seconds}`;
      this.cdr.detectChanges();
    }, 1000);
  }

  private stopRecordingTimer() {
    if (this.recordingTimerId) {
      clearInterval(this.recordingTimerId);
      this.recordingTimerId = null;
    }
  }

  // --- DEINE BESTEHENDE LOGIK ---

  startAutoFlightFromSetup() {
    this.isFlightActive = true;
    this.isFlying = true;
    this.droneService.playSavedFlight(this.droneService.selectedAutoFlight!).subscribe({
      next: (res) => console.log('Backend Start:', res),
      error: (err) => {
        console.error('Start Fehler:', err);
        this.isFlying = false;
        this.isFlightActive = false;
      }
    });
  }

  private connectWebSocket() {
    const mode = this.droneService.selectedMode;
    const WS_URL = `ws://localhost:8000/drone/${mode}`;
    this.socket = new WebSocket(WS_URL);
    this.socket.onopen = () => {
      if (mode === 'controlps') this.startControllerLoop();
    };
    this.socket.onclose = () => this.stopControllerLoop();
  }

  private sendData(data: any) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
    }
  }

  startJoystick(event: MouseEvent | TouchEvent, side: 'left' | 'right') {
    event.preventDefault();
    this.draggingSide = side;
  }

  @HostListener('window:mousemove', ['$event'])
  @HostListener('window:touchmove', ['$event'])
  handleJoystickMove(event: any) {
    if (!this.draggingSide) return;
    const clientX = event.touches ? event.touches[0].clientX : event.clientX;
    const clientY = event.touches ? event.touches[0].clientY : event.clientY;
    const root = this.draggingSide === 'left' ? this.leftJoy : this.rightJoy;
    const stick = this.draggingSide === 'left' ? this.leftStick : this.rightStick;
    const state = this.draggingSide === 'left' ? this.left : this.right;

    if (!root || !stick) return;
    const rect = root.nativeElement.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    let dx = clientX - cx;
    let dy = clientY - cy;
    const dist = Math.hypot(dx, dy);
    if (dist > this.RADIUS) {
      dx *= this.RADIUS / dist;
      dy *= this.RADIUS / dist;
    }
    stick.nativeElement.style.left = 50 + (dx / this.RADIUS) * 50 + "%";
    stick.nativeElement.style.top = 50 + (dy / this.RADIUS) * 50 + "%";
    state.x = dx / this.RADIUS;
    state.y = dy / this.RADIUS;

    if (this.droneService.selectedMode === 'controltouch') {
      this.sendData({ lx: this.left.x, ly: this.left.y, rx: this.right.x, ry: this.right.y });
    }
  }

  @HostListener('window:mouseup')
  @HostListener('window:touchend')
  stopJoystick() {
    if (!this.draggingSide) return;
    const stick = this.draggingSide === 'left' ? this.leftStick : this.rightStick;
    const state = this.draggingSide === 'left' ? this.left : this.right;
    if (stick) {
      stick.nativeElement.style.left = "50%";
      stick.nativeElement.style.top = "50%";
    }
    state.x = 0; state.y = 0;
    this.draggingSide = null;
    if (this.droneService.selectedMode === 'controltouch') {
      this.sendData({ lx: 0, ly: 0, rx: 0, ry: 0 });
    }
  }

  handleSpaceAction(isPressed: boolean) {
    if (this.droneService.selectedMode !== 'controltouch' || !isPressed) return;
    this.sendData({ takeoffLand: true });
  }

  @HostListener('window:keydown', ['$event'])
  handleKeyDown(event: KeyboardEvent) {
    if (event.key === ' ' || event.code === 'Space'){
      if(!this.isFlying) this.isFlying = true;
      if(this.isStarted) this.showafterland = true
      if(!this.isStarted) this.isStarted = true;
    }
    if (this.isFlying && this.droneService.selectedMode === 'controlkeyboard') {
      if (!this.allowedKeys.has(event.key)) return;
      event.preventDefault();
      if (event.repeat) return;
      this.sendData({ key: event.key, pressed: true });
    }
    if(this.showafterland) {
      this.showSaveModal = true;
      this.isFlying = false;
    }
  }

  @HostListener('window:keyup', ['$event'])
  handleKeyUp(event: KeyboardEvent) {
    if (this.isFlying && this.droneService.selectedMode === 'controlkeyboard') {
      if (!this.allowedKeys.has(event.key)) return;
      event.preventDefault();
      this.sendData({ key: event.key, pressed: false });
    }
  }

  private startControllerLoop() {
    this.stopControllerLoop();
    const loop = () => {
      this.controllerLoopId = setTimeout(loop, this.SEND_DT_MS);
      if (!this.isFlying || this.droneService.selectedMode !== 'controlps') return;
      const gp = this.getFirstGamepad();
      if (gp) this.processGamepadData(gp);
    };
    loop();
  }

  @HostListener('window:gamepadconnected', ['$event'])
  onGamepadConnected(event: GamepadEvent) {
    this.gamepadConnected = true;
    this.gamepadName = event.gamepad.id;
  }

  @HostListener('window:gamepaddisconnected')
  onGamepadDisconnected(): void {
    this.gamepadConnected = false;
  }

  private stopControllerLoop() {
    if (this.controllerLoopId) clearTimeout(this.controllerLoopId);
  }

  private getFirstGamepad(): Gamepad | null {
    const gamepads = navigator.getGamepads?.() ?? [];
    for (const gp of gamepads) { if (gp && gp.connected) return gp; }
    return null;
  }

  private processGamepadData(gp: Gamepad) {
    const dz = (v: number) => Math.abs(v) < this.DEADZONE ? 0 : v;
    const lx = dz(gp.axes[0] ?? 0);
    const ly = dz(gp.axes[1] ?? 0);
    const rx = dz(gp.axes[2] ?? 0);
    const l2 = gp.buttons[6]?.value ?? 0;
    const r2 = gp.buttons[7]?.value ?? 0;
    const xNow = !!gp.buttons[0]?.pressed;
    let takeoffLand = false;
    if (xNow && !this.lastXPressed) takeoffLand = true;
    this.lastXPressed = xNow;
    this.sendData({ lx, ly, rx, l2, r2, takeoffLand });
  }

  saveFlightName() {
    if (!this.flightName.trim()) return;
    this.droneService.saveFlight({ name: this.flightName.trim() }).subscribe({
      next: () => this.closeModal(),
      error: (err) => console.error('Speichern fehlgeschlagen:', err)
    });
  }

  closeModal() {
    this.isStarted = false;
    this.showafterland = false;
    this.showSaveModal = false;
    this.flightName = '';
  }

  emergencyStop() {
    // Falls noch aufgenommen wird, automatisch stoppen
    if (this.isRecording) {
      this.droneService.stopRecording().subscribe();
      this.stopRecordingTimer();
    }
    this.droneService.emergencyStop().subscribe();
    this.cleanUp();
    this.droneService.isConnected = false;
    this.droneService.selectedMode = null;
    this.router.navigate(['/']);
  }

  private cleanUp() {
    this.isFlying = false;
    this.stopControllerLoop();
    this.stopRecordingTimer();
    if (this.socket) this.socket.close();
    if (this.videoStreamSocket) this.videoStreamSocket.close();
  }

  ngOnDestroy() {
    this.cleanUp();
  }
}
