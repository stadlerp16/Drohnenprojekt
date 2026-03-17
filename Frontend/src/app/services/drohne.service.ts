import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class DroneService {
  private baseUrl = 'http://localhost:8000/drone';

  // Zentraler Status
  isConnected = false;
  selectedMode: 'controlkeyboard' | 'controlps' | 'controltouch' | null = null;

  isAutoFlight = false;
  selectedAutoFlight: string | null = null;

  constructor(private http: HttpClient) {}

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
}
