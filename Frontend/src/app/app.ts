import { Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { NgIf } from '@angular/common';
import { DroneService } from './services/drohne.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, ReactiveFormsModule, NgIf],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected readonly title = signal('SYPProjekt');

  ipForm: FormGroup;
  // Hier fehlte die Zuweisung und der richtige Typ
  isConnected: boolean = false;
  isConnecting: boolean = false;

  constructor(
    private fb: FormBuilder,
    private droneService: DroneService
  ) {
    this.ipForm = this.fb.group({
      droneIp: ['', [Validators.required]]
    });
  }

  onSubmit() {
    if (this.ipForm.valid && !this.isConnecting) {
      this.isConnecting = true;

      const ip = this.ipForm.value.droneIp;
      console.log('Sende IP an Backend:', ip);

      this.droneService.sendIpAddress(ip).subscribe({
        next: (response) => {
          console.log('Verbindung erfolgreich:', response);
          this.isConnecting = false;
          this.isConnected = true;
        },
        error: (err) => {
          console.error('Verbindung fehlgeschlagen:', err);
          this.isConnecting = false;
          this.isConnected = true;
        }
      });
    }
  }

  // Hier waren die Klammern falsch verschachtelt:
  startDrone() {
    this.droneService.startDrone().subscribe({
      next: (res) => console.log('Start erfolgreich:', res),
      error: (err) => console.error('Start Fehler:', err)
    });
  }

  stopDrone() {
    this.droneService.stopDrone().subscribe({
      next: (res) => console.log('Stopp erfolgreich:', res),
      error: (err) => console.error('Stopp Fehler:', err)
    });
  }

  emergencyStop() {

    this.isConnected = false;
    this.isConnecting = false;
    this.ipForm.reset(); //Löscht die IP aus dem Feld
    console.log('Not-Aus: Verbindung im Frontend getrennt.');
  }
}
