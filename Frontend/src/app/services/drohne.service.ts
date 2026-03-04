import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class DroneService {
  private baseUrl = 'http://localhost:8000/drone';

  isConnected = false;
  selectedMode: 'controlkeyboard' | 'controlps' | 'controltouch' | null = null;

  isAutoFlight = false;
  selectedAutoFlight: string | null = null;

  constructor(private http: HttpClient) {}

  sendIpAddress(ip: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/connect`, { ip });
  }


  getSavedFlights(): Observable<{ ok: boolean, flights: string[] }> {
    return this.http.get<{ ok: boolean, flights: string[] }>(`${this.baseUrl}/flights`);
  }


  playSavedFlight(flightName: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/play`, { name: flightName });
  }

  startDrone(): Observable<any> { return this.http.post(`${this.baseUrl}/start`, {}); }
  stopDrone(): Observable<any> { return this.http.post(`${this.baseUrl}/stop`, {}); }
  emergencyStop(): Observable<any> { return this.http.post(`${this.baseUrl}/emergency`, {}); }
}
