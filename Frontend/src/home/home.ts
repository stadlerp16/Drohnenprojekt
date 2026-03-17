import { Component, OnInit } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { NgIf, NgFor } from '@angular/common';
import { Router } from '@angular/router';
import { DroneService } from '../app/services/drohne.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [ReactiveFormsModule, NgIf, NgFor],
  templateUrl: './home.html',
  styleUrl: './home.css'
})
export class Home implements OnInit {
  ipForm: FormGroup;

  // Getrennte Zustände für die Buttons
  isAddingNew = false;
  connectingIp: string | null = null;

  isConnected = false;
  isLanded = false;
  activeIp: string | null = null;

  setupType: 'manual' | 'auto' | null = null;

  // Deine Liste mit Dummies (wird durch loadFlights ergänzt)
  savedFlights: string[] = [
    'Viereck-Parcours (Wohnzimmer)',
    "Servus"
  ];
  savedDrones: any[] = [];

  constructor(
    private fb: FormBuilder,
    public droneService: DroneService,
    public router: Router
  ) {
    this.ipForm = this.fb.group({
      droneIp: ['', [Validators.required, Validators.pattern('^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}$')]],
      courseName: ['']
    });
  }

  ngOnInit() {
    this.loadFlights();
  }

  // --- LOGIK FÜR GERÄTE ---

  onAddNewDevice() {
    if (this.ipForm.invalid) return;
    const ip = this.ipForm.value.droneIp;
    this.isAddingNew = true;
    this.connectDrone(ip, true);
  }

  handleConnection(ip: string) {
    if (this.isConnected && this.activeIp === ip) {
      this.onDisconnect();
    } else {
      this.connectingIp = ip;
      this.connectDrone(ip, false);
    }
  }

  private connectDrone(ip: string, isNew: boolean) {
    this.droneService.sendIpAddress(ip).subscribe({
      next: () => this.finishConnection(ip, isNew),
      error: () => {
        console.warn('Backend nicht erreichbar - Simuliere Verbindung');
        this.finishConnection(ip, isNew);
      }
    });
  }

  private finishConnection(ip: string, isNew: boolean) {
    this.isAddingNew = false;
    this.connectingIp = null;
    this.isConnected = true;
    this.activeIp = ip;

    if (isNew && !this.savedDrones.find(d => d.ip === ip)) {
      this.savedDrones.push({ name: 'Neue Tello Drohne', ip: ip });
    }
    this.ipForm.reset();
  }

  onDisconnect() {
    this.droneService.disconnect().subscribe({
      next: () => {
        this.isConnected = false;
        this.activeIp = null;
        this.setupType = null;
      }
    });
  }

  // --- NAVIGATION & FLUG-LOGIK ---

  setSetupType(type: 'manual' | 'auto') {
    this.setupType = type;
    this.droneService.isAutoFlight = (type === 'auto');

    // Reset der Auswahl beim Umschalten
    if (type === 'auto') {
      this.droneService.selectedMode = null;
    } else {
      this.droneService.selectedAutoFlight = null;
    }
  }

  selectMode(mode: any) {
    this.droneService.selectedMode = mode;
  }

  selectFlight(name: string) {
    this.droneService.selectedAutoFlight = name;
    // WICHTIG: Kein selectedMode mehr setzen, damit wir wissen, dass es Auto ist!
    this.droneService.selectedMode = null;
  }

  loadFlights() {
    this.droneService.getSavedFlights().subscribe(res => {
      if (res?.ok && res.flights) {
        // Bestehende Dummies behalten und neue vom Backend hinzufügen (ohne Dopplungen)
        const combined = [...this.savedFlights, ...res.flights];
        this.savedFlights = [...new Set(combined)];
      }
    });
  }

  onContinue() {
    // 1. MANUELLER MODUS
    if (this.setupType === 'manual') {
      if (this.droneService.selectedMode) {
        this.droneService.isAutoFlight = false;
        // Wir setzen zur Sicherheit nochmal isConnected auf true,
        // damit die Zielseite uns nicht direkt wieder rauswirft.
        this.droneService.isConnected = true;
        this.router.navigate(['/control']);
      }
    }
    // 2. AUTOMATISCHER MODUS
    else if (this.setupType === 'auto') {
      const flightName = this.droneService.selectedAutoFlight;

      if (flightName) {
        this.droneService.isAutoFlight = true;
        this.droneService.isConnected = true; // WICHTIG gegen den Redirect!

        // Backend-Call: Wir sagen der Drohne, sie soll JETZT losfliegen
        this.droneService.playSavedFlight(flightName).subscribe({
          next: () => {
            console.log('Route erfolgreich gestartet');
            this.router.navigate(['/control']);
          },
          error: (err) => {
            console.error('Backend Fehler beim Play, navigiere trotzdem...', err);
            // Wir navigieren trotzdem, damit du siehst, ob es am Frontend liegt
            this.router.navigate(['/control']);
          }
        });
      }
    }
  }

  saveFlightCourse() {}
}
