import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class DroneService {

  private baseUrl = 'http://localhost:8000/drone';

  constructor(private http: HttpClient) {
  }

  // Die Methode baut sich die URL dynamisch zusammen
  sendIpAddress(ip: string): Observable<any> {
    const payload = {ipAddress: ip};

    return this.http.post(`${this.baseUrl}/connect`, payload);
  }
}
