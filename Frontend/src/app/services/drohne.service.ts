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
  private isManuallyDisconnected = false;

  isAutoFlight = false;
  selectedAutoFlight: string | null = null;
  activeIp: string | null = null;

  public telemetry: any = {
    bat: 0,
    speed: 0,
    current_height: 0,
    pitch: 0,
    roll: 0,
    yaw: 0,
    total_distance_cm: 0,
    flight_duration: 0,
  };
  connectedIp: string = '';

  private socket: WebSocket | null = null;

  constructor(private http: HttpClient) {
    this.initTelemetryWebSocket();
  }




  sendIpAddress(ip: string): Observable<any> {
    this.isManuallyDisconnected = false; // Sperre aufheben
    this.connectedIp = ip;
    this.activeIp = ip;

    if (!this.socket || this.socket.readyState === WebSocket.CLOSED) {
      this.initTelemetryWebSocket();
    }

    return this.http.post(`${this.baseUrl}/connect`, { ip });
  }

  disconnect(): Observable<any> {
    this.isManuallyDisconnected = true; // Wir sagen dem Service: "Stopp, ich will das!"
    this.isConnected = false;
    this.activeIp = null;

    // WebSocket hart schließen
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }

    return this.http.post(`${this.baseUrl}/disconnect`, {});
  }

  getSavedFlights(): Observable<{ ok: boolean, flights: string[] }> {
    return this.http.get<{ ok: boolean, flights: string[] }>(`${this.baseUrl}/flights`);
  }


  playSavedFlight(flightName: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/play-flight`, { name: flightName });
  }

  saveFlight(payload: { name: string }): Observable<any> {
    return this.http.post(`${this.baseUrl}/save-flight-name`, payload);
  }

  emergencyStop(): Observable<any> {
    return this.http.post(`${this.baseUrl}/emergency`, {});
  }

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

  getVideoStreamSocket(): WebSocket {
    return new WebSocket('ws://localhost:8000/video/getlivestream');
  }


  public selectedColor: 'r' | 'b' | 'p' = 'b';


  private initTelemetryWebSocket() {
    this.socket = new WebSocket(this.wsUrl);

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        this.telemetry = {
          bat: data.battery || 0,
          current_height: data.current_height || 0,
          speed: data.speed || 0,
          pitch: data.pitch || 0,
          roll: data.roll || 0,
          yaw: data.yaw || 0,
          total_distance_cm: data.total_distance_cm || 0,
          flight_duration: data.flight_duration || 0,
        };

        console.log('Telemetrie Update:', this.telemetry);
      } catch (err) {
        console.error('Fehler beim Parsen der WebSocket-Daten:', err);
      }
    };

    this.socket.onopen = () => {
      console.log('WebSocket Telemetrie: Verbunden');
      this.isManuallyDisconnected = false;
    };

    this.socket.onerror = (err: any) => console.error('WebSocket Fehler:', err);

    this.socket.onclose = () => {
      if (!this.isManuallyDisconnected) {
        console.warn('WebSocket ungewollt geschlossen. Reconnect in 2s...');
        setTimeout(() => this.initTelemetryWebSocket(), 2000);
      } else {
        console.log('WebSocket absichtlich geschlossen. Kein Reconnect gestartet.');
      }
    };
  }
}
