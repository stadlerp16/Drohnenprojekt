import { Component, OnInit } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { NgIf, NgFor, CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { DroneService } from '../app/services/drohne.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [ReactiveFormsModule, NgIf, NgFor, CommonModule],
  templateUrl: './home.html',
  styleUrl: './home.css'
})
export class Home implements OnInit {
  ipForm: FormGroup;

  isAddingNew = false;
  connectingIp: string | null = null;
  setupType: 'manual' | 'auto' | null = null;

  public ledMatrix: number[][] = Array(8).fill(0).map(() => Array(8).fill(0));

  savedFlights: string[] = ['Viereck-Parcours', 'Servus-Flug'];
  savedDrones: any[] = [];

  constructor(
    private fb: FormBuilder,
    public droneService: DroneService, // Wichtig: public für Zugriff im HTML
    public router: Router
  ) {
    this.ipForm = this.fb.group({
      droneIp: ['', [Validators.required, Validators.pattern('^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}$')]]
    });
  }

  ngOnInit() {
    this.loadFlights();
    // Falls wir bereits verbunden sind (aus dem Service), stellen wir savedDrones wieder her
    if (this.droneService.isConnected && this.droneService.activeIp) {
      if (!this.savedDrones.find(d => d.ip === this.droneService.activeIp)) {
        this.savedDrones.push({ name: 'Tello Drohne', ip: this.droneService.activeIp });
      }
    }
  }

  // --- LED MATRIX LOGIK ---
  toggleLed(row: number, col: number) {
    this.ledMatrix[row][col] = this.ledMatrix[row][col] === 0 ? 1 : 0;
    this.droneService.sendLedUpdate(this.ledMatrix).subscribe({
      next: (res) => console.log('Matrix gesendet', res),
      error: (err) => console.error('Matrix Fehler', err)
    });
  }

  sendCurrentMatrix() {
    if (!this.droneService.isConnected) return;

    this.droneService.sendLedUpdate(this.ledMatrix).subscribe({
      next: (res) => {
        console.log('Matrix manuell gesendet:', res);
      },
      error: (err) => console.error('Fehler beim manuellen Senden der Matrix:', err)
    });
  }

  clearMatrix() {
    this.ledMatrix.forEach(row => row.fill(0));
    this.droneService.sendLedUpdate(this.ledMatrix).subscribe();
  }

  sendScrollingText(text: string) {
    if (!text || !this.droneService.isConnected) return;
    this.droneService.sendControlCommand(text).subscribe({
      next: () => console.log(`Text gesendet: ${text}`),
      error: (err) => console.error('Fehler Text-Senden', err)
    });
  }

  // --- VERBINDUNGS LOGIK ---
  onAddNewDevice() {
    if (this.ipForm.invalid) return;
    const ip = this.ipForm.value.droneIp;
    this.isAddingNew = true;
    this.connectDrone(ip, true);
  }

  handleConnection(ip: string) {
    // Check gegen Service Status
    if (this.droneService.isConnected && this.droneService.activeIp === ip) {
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
        console.warn('Backend offline - Simuliere Verbindung für Testmodus');
        this.finishConnection(ip, isNew);
      }
    });
  }

  private finishConnection(ip: string, isNew: boolean) {
    this.isAddingNew = false;
    this.connectingIp = null;

    // Status global im Service speichern
    this.droneService.isConnected = true;
    this.droneService.activeIp = ip;

    if (isNew && !this.savedDrones.find(d => d.ip === ip)) {
      this.savedDrones.push({ name: 'Neue Tello Drohne', ip: ip });
    }
    this.ipForm.reset();
  }

  onDisconnect() {
    this.droneService.disconnect().subscribe({
      next: () => this.resetServiceStatus(),
      error: () => this.resetServiceStatus() // Auch bei Fehler lokal trennen
    });
  }

  private resetServiceStatus() {
    this.droneService.isConnected = false;
    this.droneService.activeIp = null;
    this.setupType = null;
    this.droneService.selectedMode = null;
    this.droneService.selectedAutoFlight = null;
  }

  // --- NAVIGATION & MODI ---
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
  }

  loadFlights() {
    this.droneService.getSavedFlights().subscribe(res => {
      if (res?.ok && res.flights) {
        const combined = [...this.savedFlights, ...res.flights];
        this.savedFlights = [...new Set(combined)];
      }
    });
  }

  onContinue() {
    if (this.setupType === 'manual' && this.droneService.selectedMode) {
      this.router.navigate(['/control']);
    } else if (this.setupType === 'auto' && this.droneService.selectedAutoFlight) {
      this.router.navigate(['/control']);
    }
  }
}
