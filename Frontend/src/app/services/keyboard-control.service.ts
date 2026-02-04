import { Injectable, NgZone } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class KeyboardControlService {
  private keys = new Set<string>();

  constructor(private zone: NgZone) {
    this.zone.runOutsideAngular(() => {
      window.addEventListener('keydown', e => this.keys.add(e.key.toLowerCase()));
      window.addEventListener('keyup', e => this.keys.delete(e.key.toLowerCase()));
      window.addEventListener('blur', () => this.keys.clear());
    });
  }

  getControls() {
    let roll = 0;
    let pitch = 0;
    let yaw = 0;
    let throttle = 0;

    if (this.keys.has('w')) pitch += 1;
    if (this.keys.has('s')) pitch -= 1;

    if (this.keys.has('a')) roll -= 1;
    if (this.keys.has('d')) roll += 1;

    /*if (this.keys.has('q')) yaw -= 1;
    if (this.keys.has('e')) yaw += 1;

    if (this.keys.has(' ')) throttle += 1;
    if (this.keys.has('shift')) throttle -= 1;*/

    return { roll, pitch };
  }
}
