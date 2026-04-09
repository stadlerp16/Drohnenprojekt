import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import {interval, Observable, startWith, switchMap} from 'rxjs';


@Injectable({ providedIn: 'root' })
export class DroneService {
  private baseUrl = 'http://localhost:8000/drone';
  private wsUrl = 'ws://localhost:8000/drone/telemetrie';

  // Zentraler Status
  isConnected = false;
  selectedMode: 'controlkeyboard' | 'controlps' | 'controltouch' | null = null;

  isAutoFlight = false;
  selectedAutoFlight: string | null = null;
  activeIp: string | null = null;

  public telemetry: any = {
    bat: 0,
    speed: 0,
    h: 0,
    pitch: 0,
    roll: 0,
    yaw: 0
  };

  private socket: WebSocket | null = null;

  constructor(private http: HttpClient) {
    this.initTelemetryWebSocket();
  }

  sendIpAddress(ip: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/connect`, { ip });

  }

  disconnect(): Observable<any> {
    console.log('Service: Sende Disconnect-Anfrage an Backend...');
    // Wir senden einen POST-Request ohne Body an den disconnect-Endpunkt
    return this.http.post(`${this.baseUrl}/disconnect`, {});
  }

  getSavedFlights(): Observable<{ ok: boolean, flights: string[] }> {
    return this.http.get<{ ok: boolean, flights: string[] }>(`${this.baseUrl}/flights`);
  }


  playSavedFlight(flightName: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/play-flight`, { name: flightName });
  }

  saveFlight(payload: { ip: string, courseName: string }): Observable<any> {
    return this.http.post(`${this.baseUrl}/save-course`, payload);
  }

  startDrone(): Observable<any> {
    return this.http.post(`${this.baseUrl}/start`, {});
  }

  stopDrone(): Observable<any> {
    return this.http.post(`${this.baseUrl}/stop`, {});
  }

  emergencyStop(): Observable<any> {
    return this.http.post(`${this.baseUrl}/emergency`, {});
  }

  // drone.service.ts

// Ändere die Methode so ab:
  sendLedUpdate(pattern: number[][]): Observable<any> {
    const map: { [key: number]: string } = {
      0: '0',
      1: 'r',
      2: 'b',
      3: 'p'
    };

    const matrix = pattern.flat().map(pixel => map[pixel] || '0').join('');
    return this.http.post(`${this.baseUrl}/led`, { matrix });
  }

  sendControlCommand(command: string) {
    return this.http.post(`${this.baseUrl}/command`, {
      command: command,
      color: this.selectedColor
    });
  }

  public selectedColor: 'r' | 'b' | 'p' = 'b';

  private initTelemetryWebSocket() {
    this.socket = new WebSocket(this.wsUrl);

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // Mapping der Backend-Keys (battery, height) auf deine Frontend-Variablen (bat, h)
        this.telemetry = {
          bat: data.battery || 0,   // Backend sendet "battery"
          h: data.height || 0,      // Backend sendet "height"
          speed: data.speed || 0,   // Bleibt gleich
          pitch: data.pitch || 0,   // Bleibt gleich
          roll: data.roll || 0,     // Bleibt gleich
          yaw: data.yaw || 0        // Bleibt gleich
        };

        console.log('Telemetrie Update:', this.telemetry);
      } catch (err) {
        console.error('Fehler beim Parsen der WebSocket-Daten:', err);
      }
    };

    this.socket.onopen = () => console.log('WebSocket Telemetrie: Verbunden');
    this.socket.onerror = (err: any) => console.error('WebSocket Fehler:', err);

    this.socket.onclose = () => {
      console.warn('WebSocket geschlossen. Reconnect in 2s...');
      setTimeout(() => this.initTelemetryWebSocket(), 2000);
    };
  }
}
