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

  isAddingNew = false;
  connectingIp: string | null = null;

  isConnected = false;
  isLanded = false;
  activeIp: string | null = null;
  setupType: 'manual' | 'auto' | null = null;
  ledMatrix: boolean[][] = [
    [true,  true,  true,  true,  true,  false,  false,  false],
    [false, false, true,  false, false, false,  false, false],
    [false, false, true,  true, true, true,  true, true],
    [false, false, true,  false, false, true,  false, false],
    [false, false, true,  false, false, true,  false, false],
    [false, false, false, false, false, true, false, false],
    [false, false, false, false, false, true, false, false],
    [false, false, false, false, false, false, false, false]
  ];

  savedFlights: string[] = [
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

  toggleLed(row: number, col: number) {
    // Lokalen Status umschalten
    this.ledMatrix[row][col] = !this.ledMatrix[row][col];

    // Ans Backend senden
    this.droneService.sendLedUpdate(row, col, this.ledMatrix[row][col]).subscribe({
      next: () => console.log(`LED [${row},${col}] ist jetzt ${this.ledMatrix[row][col]}`),
      error: (err) => console.error('Fehler beim Senden der LED-Daten', err)
    });
  }
  clearMatrix() {
    // Geht durch jede Zeile und setzt alle Spalten auf false
    this.ledMatrix.forEach(row => row.fill(false));
  }


  sendScrollingText(text: string) {
    if (!text || !this.isConnected) return;

    const command = `mled s b l 5 ${text}`;

    this.droneService.sendControlCommand(command).subscribe({
      next: () => {
        console.log(`Laufschrift gesendet: ${text}`);
        // Optional: Matrix in der UI leeren, da die Drohne nun Text anzeigt
        this.clearMatrix();
      },
      error: (err: any) => console.error('Fehler beim Senden der Laufschrift', err)
    });
  }


  //LOGIK FÜR GERÄTE

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

  //NAVIGATION & FLUG-LOGIK

  setSetupType(type: 'manual' | 'auto') {
    this.setupType = type;
    this.droneService.isAutoFlight = (type === 'auto');

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
    if (this.setupType === 'manual') {
      if (this.droneService.selectedMode) {
        this.droneService.isAutoFlight = false;
        this.droneService.isConnected = true;
        // WICHTIG: Prüfe ob deine Route '/control' oder '/dashboard' heißt!
        this.router.navigate(['/control']);
      }
    }
    else if (this.setupType === 'auto') {
      const flightName = this.droneService.selectedAutoFlight;
      if (flightName) {
        // Wir setzen NUR die Variablen im Service
        this.droneService.isAutoFlight = true;
        this.droneService.isConnected = true;

        // Wir navigieren NUR. Der Befehl wird erst im Dashboard gefeuert.
        console.log('Navigiere zum Dashboard, Autopilot wird dort gestartet...');
        this.router.navigate(['/control']);
      }
    }
  }

  saveFlightCourse() {}
}
