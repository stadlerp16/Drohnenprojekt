import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import {interval, Observable, startWith, switchMap} from 'rxjs';

@Injectable({ providedIn: 'root' })
export class DroneService {
  private baseUrl = 'http://localhost:8000/drone';

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

  constructor(private http: HttpClient) {
    this.startTelemetryPolling();
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
    return this.http.post(`${this.baseUrl}/play`, { name: flightName });
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

  private startTelemetryPolling() {
    interval(500).pipe(
      startWith(0),
      switchMap(() => this.http.get(`${this.baseUrl}/telemetry`))
    ).subscribe({
      next: (data: any) => {
        if (data) {
          this.telemetry = data;
        }
      },
      error: (err) => console.log('Warten auf Telemetrie-Daten...')
    });
  }
}
