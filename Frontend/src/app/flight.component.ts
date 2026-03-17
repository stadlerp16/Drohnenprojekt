import { Component, OnDestroy } from '@angular/core';
import { KeyboardControlService } from './services/keyboard-control.service';
import { DroneSocketService } from './services/drohne-socket.service';

@Component({
  selector: 'app-flight',
  template: `<p>WASD Steuerung aktiv</p>`
})
export class FlightComponent implements OnDestroy {
  private intervalId: any;

  constructor(
    private keyboard: KeyboardControlService,
    private socket: DroneSocketService
  ) {
    this.startFlightLoop();
  }

  startFlightLoop() {
    this.socket.connect();

    this.intervalId = setInterval(() => {
      const controls = this.keyboard.getControls();
      this.socket.sendControls(controls);
    }, 50); // 20 Hz
  }

  ngOnDestroy() {
    clearInterval(this.intervalId);
    this.socket.disconnect();
  }
}
