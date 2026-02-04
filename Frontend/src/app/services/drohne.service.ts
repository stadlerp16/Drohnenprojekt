import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class DroneService {
  // Wir nutzen hier deine definierte Basis-URL
  private baseUrl = 'http://localhost:8080/api/drone';

  constructor(private http: HttpClient) {}

  sendIpAddress(ip: string): Observable<any> {
    const payload = { ipAddress: ip };
    // Nutzt baseUrl -> Ergebnis: http://localhost:8080/api/drone/connect
    return this.http.post(`${this.baseUrl}/connect`, payload);
  }

  startDrone(): Observable<any> {
    // Geändert von apiUrl zu baseUrl -> Ergebnis: http://localhost:8080/api/drone/start
    return this.http.post(`${this.baseUrl}/start`, {});
  }

  stopDrone(): Observable<any> {
    // Geändert von apiUrl zu baseUrl -> Ergebnis: http://localhost:8080/api/drone/stop
    return this.http.post(`${this.baseUrl}/stop`, {});
  }
}
