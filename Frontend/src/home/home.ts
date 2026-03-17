import { Component, OnInit, signal } from '@angular/core';
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
  // Signals & Status
  protected readonly title = signal('DroneControl');
  ipForm: FormGroup;
  isConnecting = false;
  isConnected = false;
  isLanded = false;

  // Auswahl-Logik (aus der App-Klasse übernommen)
  setupType: 'manual' | 'auto' | null = null;
  savedFlights: string[] = [];

  constructor(
    private fb: FormBuilder,
    public droneService: DroneService,
    public router: Router
  ) {
    // Formular initialisieren (Inklusive courseName für späteres Speichern)
    this.ipForm = this.fb.group({
      droneIp: ['', Validators.required],
      courseName: ['']
    });
  }

  ngOnInit() {
    this.resetComponentState();
    this.loadFlights();
  }

  // --- Initialisierung & Daten ---

  private resetComponentState() {
    this.isConnected = false;
    this.isConnecting = false;
    this.isLanded = false;
    this.setupType = null;
    this.ipForm.enable();
    this.ipForm.reset();
    this.droneService.selectedMode = null;
    this.droneService.selectedAutoFlight = null;
  }

  loadFlights() {
    this.droneService.getSavedFlights().subscribe({
      next: (res) => {
        if (res && res.ok) this.savedFlights = res.flights;
      },
      error: () => console.log('Kein Backend erreichbar für Flüge')
    });
  }

  // --- Modus & Auswahl ---

  setSetupType(type: 'manual' | 'auto') {
    this.setupType = type;
    this.droneService.isAutoFlight = (type === 'auto');
    // Resets bei Moduswechsel
    this.droneService.selectedMode = null;
    this.droneService.selectedAutoFlight = null;
  }

  selectMode(mode: 'controlps' | 'controlkeyboard' | 'controltouch') {
    this.droneService.selectedMode = mode;
  }

  selectFlight(name: string) {
    this.droneService.selectedAutoFlight = name;
    // Dummy-Mode setzen, damit der "Weiter" Button aktiv wird
    this.droneService.selectedMode = 'controltouch';
  }

  // --- Aktionen ---

  onSubmit() {
    if (this.ipForm.valid && !this.isConnecting) {
      this.isConnecting = true;
      const ip = this.ipForm.value.droneIp;

      this.droneService.sendIpAddress(ip).subscribe({
        next: () => {
          this.isConnecting = false;
          this.isConnected = true;
        },
        error: () => {
          // Fallback für Tests: trotzdem fortfahren
          this.isConnecting = false;
          this.isConnected = true;
          console.warn('Verbindung fehlgeschlagen, aktiviere Test-Modus');
        }
      });
    }
  }

  onDisconnect() {
    this.droneService.disconnect().subscribe({
      next: (res) => {
        console.log('Backend: Drohne erfolgreich getrennt', res);
        this.resetComponentState();
      },
      error: (err) => {
        console.error('Fehler beim Trennen:', err);
        this.isConnected = false; // Status trotzdem zurücksetzen
        this.ipForm.enable();
      }
    });
  }

  onDroneLanded() {
    this.isLanded = true;
    this.ipForm.get('courseName')?.setValidators([Validators.required]);
    this.ipForm.get('courseName')?.updateValueAndValidity();
  }

  saveFlightCourse() {
    const courseControl = this.ipForm.get('courseName');
    if (courseControl?.valid) {
      const payload = {
        ip: this.ipForm.value.droneIp,
        courseName: courseControl.value
      };

      this.droneService.saveFlight(payload).subscribe(() => {
        this.isLanded = false;
        courseControl.reset();
        this.loadFlights(); // Liste nach dem Speichern aktualisieren
      });
    }
  }

  onContinue() {
    if (this.droneService.selectedMode) {
      this.router.navigate(['/control']);
    }
  }
}
