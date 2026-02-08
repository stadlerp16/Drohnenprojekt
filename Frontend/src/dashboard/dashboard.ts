import { Component } from '@angular/core';
import {DroneService} from '../app/services/drohne.service';
import {Router} from '@angular/router';
import { NgIf, NgClass } from '@angular/common';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [NgIf, NgClass],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class Dashboard {
  isFlying: boolean = false;
  controlMode: 'keyboard' | 'controller' | null = null;   //Zu beginn nichts

  constructor(private droneService: DroneService, private router: Router) {}

  selectMode(mode: 'keyboard' | 'controller') {
    if (!this.isFlying) {
      this.controlMode = mode;
      console.log('Steuerungsmodus gewählt:', mode);
    }
  }

  startDrone() {
    if (!this.controlMode) {
      alert('Bitte wählen Sie zuerst einen Steuerungsmodus!');
      return;
    }

    this.droneService.startDrone().subscribe({
      next: (res) => {
        this.isFlying = true; // Sperrt die Auswahl
        console.log('Drohne gestartet');
      },
      error: (err) => console.error(err)
    });
  }

  stopDrone() {
    this.droneService.stopDrone().subscribe({
      next: (res) => {
        this.isFlying = false; // Gibt die Auswahl wieder frei
        console.log('Drohne gelandet/gestoppt');
      },
      error: (err) => console.error(err)
    });
  }

  emergencyStop() {
    this.droneService.emergencyStop().subscribe({
      next: (res) => console.log('Not-Aus erfolgreich gesendet'),
      error: (err) => console.error('Not-Aus Fehler:', err)
    });
    this.router.navigate(['/']);
    this.isFlying = false;
  }

}
