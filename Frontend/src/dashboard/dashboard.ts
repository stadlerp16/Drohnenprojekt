import { Component, HostListener, OnDestroy, OnInit} from '@angular/core';
import { DroneService } from '../app/services/drohne.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class Dashboard implements OnDestroy , OnInit {
  isFlying: boolean = true;
  private socket: WebSocket | null = null;

  //CONTROLLER KONFIGURATION
  private readonly DEADZONE = 0.08;
  private readonly SEND_HZ = 20;
  private readonly SEND_DT_MS = 1000 / this.SEND_HZ;
  private controllerLoopId: any = null;
  private lastXPressed = true;

  private readonly allowedKeys = new Set([
    "w", "a", "s", "d", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " ", "Space"
  ]);

  constructor(protected droneService: DroneService, private router: Router) {}

  ngOnInit(){
    this.connectWebSocket();
  }
  //WEBSOCKET LOGIK

  private connectWebSocket() {
    const mode = this.droneService.selectedMode;
    // Dynamischer Pfad: /keyboard oder /controller
    const WS_URL = `ws://localhost:8000/drone/${mode}`;

    this.socket = new WebSocket(WS_URL);
    this.socket.onopen = () => {
      console.log(`WS verbunden: ${mode}`);
      if (mode === 'controlps') {
        this.startControllerLoop(); // Starte Polling wenn Controller gewählt
      }
    };
    this.socket.onclose = () => this.stopControllerLoop();
  }

  private sendData(data: any) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
    }
  }

  //TASTATUR LOGIK

  @HostListener('window:keydown', ['$event'])
  handleKeyDown(event: KeyboardEvent) {
    if (this.isFlying && this.droneService.selectedMode === 'controlkeyboard') {
      if (!this.allowedKeys.has(event.key)) return;
      event.preventDefault();
      if (event.repeat) return;
      this.sendData({ key: event.key, pressed: true });
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

  //CONTROLLER LOGIK

  private startControllerLoop() {
    this.stopControllerLoop(); // Sicherstellen, dass kein alter Loop läuft
    const loop = () => {
      if (!this.isFlying || this.droneService.selectedMode !== 'controlps') return;

      const gp = this.getFirstGamepad();
      if (gp) {
        this.processGamepadData(gp);
      }
      this.controllerLoopId = setTimeout(loop, this.SEND_DT_MS);
    };
    loop();
  }

  private stopControllerLoop() {
    if (this.controllerLoopId) {
      clearTimeout(this.controllerLoopId);
      this.controllerLoopId = null;
    }
  }

  private getFirstGamepad(): Gamepad | null {
    const gamepads = navigator.getGamepads();
    for (const gp of gamepads) {
      if (gp && gp.connected) return gp;
    }
    return null;
  }

  private processGamepadData(gp: Gamepad) {
    // Hilfsfunktionen für Deadzone und Clamp
    const dz = (v: number) => Math.abs(v) < this.DEADZONE ? 0 : v;
    const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

    // Mapping
    const lx = dz(gp.axes[0] ?? 0);
    const ly = dz(gp.axes[1] ?? 0);
    const rx = dz(gp.axes[2] ?? 0);

    // Trigger (L2 / R2)
    const l2 = clamp01(gp.buttons[6]?.value ?? 0);
    const r2 = clamp01(gp.buttons[7]?.value ?? 0);

    // X (Cross) Button für Takeoff/Land (Flankenerkennung)
    const xNow = !!gp.buttons[0]?.pressed;
    let takeoffLand = false;
    if (xNow && !this.lastXPressed) takeoffLand = true;
    this.lastXPressed = xNow;

    this.sendData({ lx, ly, rx, l2, r2, takeoffLand });
  }


  startDrone() {
    this.droneService.startDrone().subscribe({
      next: () => {
        this.isFlying = true;
        this.connectWebSocket();
      },
      error: (err) => console.error('Start fehlgeschlagen:', err)
    });
  }

  stopDrone() {
    this.droneService.stopDrone().subscribe({
      next: () => this.cleanUp(),
      error: (err) => console.error('Stop fehlgeschlagen:', err)
    });
  }

  emergencyStop() {
    this.droneService.emergencyStop().subscribe();
    this.cleanUp();
    this.droneService.isConnected = false;
    this.droneService.selectedMode = null;
    this.router.navigate(['/']);
  }

  private cleanUp() {
    this.isFlying = false;
    this.stopControllerLoop();
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  ngOnDestroy() {
    this.cleanUp();
  }
}
