import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class DroneService {
  private baseUrl = 'http://localhost:8000/drone';

  // Zentraler Status
  isConnected = false;
  selectedMode: 'controlkeyboard' | 'controlps' | 'controltouch' | null = null;

  constructor(private http: HttpClient) {}

  sendIpAddress(ip: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/connect`, { ip });
  }

  startDrone(): Observable<any> { return this.http.post(`${this.baseUrl}/start`, {}); }
  stopDrone(): Observable<any> { return this.http.post(`${this.baseUrl}/stop`, {}); }
  emergencyStop(): Observable<any> { return this.http.post(`${this.baseUrl}/emergency`, {}); }
}
