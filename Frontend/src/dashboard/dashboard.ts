import { Component } from '@angular/core';
import {DroneService} from '../app/services/drohne.service';
import {Router} from '@angular/router';
//import { NgIf, NgClass } from '@angular/common';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class Dashboard {
  isFlying: boolean = false;

  constructor(protected droneService: DroneService, private router: Router) {}


  startDrone() {
    this.droneService.startDrone().subscribe({
      next: (res) => {
        this.isFlying = true;
        console.log('Drohne gestartet. Modus:', this.droneService.selectedMode);
      },
      error: (err) => console.error('Start Fehler:', err)
    });
  }

  stopDrone() {
    this.droneService.stopDrone().subscribe({
      next: (res) => {
        this.isFlying = false;
        console.log('Drohne gelandet/gestoppt');
      },
      error: (err) => console.error('Stop Fehler:', err)
    });
  }

  emergencyStop() {
    this.droneService.emergencyStop().subscribe();
    this.isFlying = false;

    // Alles im Service resetten -> Damit springt die Startseite in den Anfangszustand
    this.droneService.isConnected = false;
    this.droneService.selectedMode = null;

    // Zurück navigieren
    this.router.navigate(['/']);
  }

}
