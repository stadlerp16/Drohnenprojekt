import {Injectable} from '@angular/core';

@Injectable({ providedIn: 'root' })
export class DroneSocketService {
  private socket?: WebSocket;

  connect() {
    this.socket = new WebSocket('http://localhost:8000/drone/control');
  }

  sendControls(controls: any) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(controls));
    }
  }

  disconnect() {
    this.socket?.close();
  }
}
