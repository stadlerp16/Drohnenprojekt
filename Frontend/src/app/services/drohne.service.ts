import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import {interval, Observable, startWith, switchMap} from 'rxjs';

@Injectable({ providedIn: 'root' })
export class DroneService {
  private baseUrl = 'http://localhost:8000/drone';
  private wsUrl = 'ws://localhost:8000/drohne/telemetry';

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

  sendLedUpdate(row: number, col: number, state: boolean): Observable<any> {
    return this.http.post(`${this.baseUrl}/led`, { row, col, active: state });
  }

  sendControlCommand(command: string) {
    return this.http.post(`${this.baseUrl}/command`, { command: command });
  }

  private initTelemetryWebSocket() {
    this.socket = new WebSocket(this.wsUrl);

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // Die Telemetrie-Daten werden hier direkt aktualisiert
        this.telemetry = {
          bat: data.bat || 0,
          speed: data.speed || 0,
          h: data.h || 0,
          pitch: data.pitch || 0,
          roll: data.roll || 0,
          yaw: data.yaw || 0
        };
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
