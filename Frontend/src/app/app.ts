import { Component, signal, OnInit } from '@angular/core';
import { Router, RouterOutlet } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { NgIf, NgFor } from '@angular/common';
import { DroneService } from './services/drohne.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, ReactiveFormsModule, NgIf, NgFor],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit {
  protected readonly title = signal('DroneControl');

  ipForm: FormGroup;
  isConnecting: boolean = false;
  isConnected: boolean = false;

  // Auswahl-Logik
  setupType: 'manual' | 'auto' | null = null;
  savedFlights: string[] = [];

  constructor(private fb: FormBuilder, public droneService: DroneService, public router: Router) {
    this.ipForm = this.fb.group({ droneIp: ['', [Validators.required]] });
  }

  ngOnInit() {
    this.loadFlights();
  }

  loadFlights() {
    this.droneService.getSavedFlights().subscribe({
      next: (res) => { if (res.ok) this.savedFlights = res.flights; },
      error: () => console.log('Kein Backend erreichbar für Flüge')
    });
  }

  setSetupType(type: 'manual' | 'auto') {
    this.setupType = type;
    this.droneService.isAutoFlight = (type === 'auto');
    // Resets
    this.droneService.selectedMode = null;
    this.droneService.selectedAutoFlight = null;
  }

  selectMode(mode: any) { this.droneService.selectedMode = mode; }

  selectFlight(name: string) {
    this.droneService.selectedAutoFlight = name;
    // Dummy-Mode setzen, damit der "Weiter" Button im HTML aktiv wird
    this.droneService.selectedMode = 'controltouch';
  }

  onSubmit() {
    if (this.ipForm.valid) {
      this.isConnecting = true;
      this.droneService.sendIpAddress(this.ipForm.value.droneIp).subscribe({
        next: () => { this.isConnecting = false; this.isConnected = true; },
        error: () => { this.isConnecting = false; this.isConnected = true; } // Zum Testen
      });
    }
  }

  onContinue() {
    this.router.navigate(['/control']);
  }
}
