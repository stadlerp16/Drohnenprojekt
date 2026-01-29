import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class DroneService {

  //Endpunktverbindung ins Backend
  private apiUrl = 'http://localhost:8080/api/drone/connect';

  constructor(private http: HttpClient) {}

  sendIpAddress(ip: string): Observable<any> {
    //Daten in JSON verpacken
    const payload = { ipAddress: ip };
    return this.http.post(this.apiUrl, payload);
  }
}
