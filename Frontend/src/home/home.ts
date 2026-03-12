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
  isConnecting = false;
  isConnected = false;
  static isLanded = true;
  activeIp: string | null = null;

  setupType: 'manual' | 'auto' | null = null;
  savedFlights: string[] = [];

  // Diese Liste würde normalerweise von droneService.getSavedDrones() kommen
  savedDrones: any[] = [];



  static getIsLanded(): boolean {
    return this.isLanded;
  }

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
    // Hier könntest du auch die gespeicherten Drohnen vom Backend laden
  }

  // --- LOGIK FÜR GERÄTE ---

  onAddNewDevice() {
    if (this.ipForm.invalid) return;
    const ip = this.ipForm.value.droneIp;
    this.connectDrone(ip, true);
  }

  handleConnection(ip: string) {
    if (this.isConnected && this.activeIp === ip) {
      this.onDisconnect();
    } else {
      this.connectDrone(ip, false);
    }
  }

  private connectDrone(ip: string, isNew: boolean) {
    this.isConnecting = true;
    this.droneService.sendIpAddress(ip).subscribe({
      next: () => {
        this.finishConnection(ip, isNew);
      },
      error: () => {
        // Fallback für Testzwecke
        console.warn('Backend nicht erreichbar - Simuliere Verbindung');
        this.finishConnection(ip, isNew);
      }
    });
  }

  private finishConnection(ip: string, isNew: boolean) {
    this.isConnecting = false;
    this.isConnected = true;
    this.activeIp = ip;

    if (isNew && !this.savedDrones.find(d => d.ip === ip)) {
      this.savedDrones.push({name: 'Neue Drohne', ip: ip});
      // Hier optional: this.droneService.saveDeviceToDb({ip}).subscribe();
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

  // --- MODUS & NAVIGATION ---

  setSetupType(type: 'manual' | 'auto') {
    this.setupType = type;
    this.droneService.isAutoFlight = (type === 'auto');
    this.droneService.selectedMode = null;
    this.droneService.selectedAutoFlight = null;
  }

  selectMode(mode: any) {
    this.droneService.selectedMode = mode;
  }

  selectFlight(name: string) {
    this.droneService.selectedAutoFlight = name;
    this.droneService.selectedMode = 'controltouch';
  }

  loadFlights() {
    this.droneService.getSavedFlights().subscribe(res => {
      if (res?.ok) this.savedFlights = res.flights;
    });
  }

  onContinue() {
    if (this.droneService.selectedMode) this.router.navigate(['/control']);
  }

  saveFlightCourse() {
    const name = this.ipForm.get('courseName')?.value;
    if (name && this.droneService.activeIp) {

      this.droneService.saveFlight({
        ip: this.droneService.activeIp,
        courseName: name
      }).subscribe({
        next: () => {
          this.droneService.setLanded(false); // Status über Service ändern
          this.ipForm.get('courseName')?.reset();
          this.loadFlights();
        }
      });
    }
  }
}
