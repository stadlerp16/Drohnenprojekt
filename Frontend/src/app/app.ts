import { Component, signal } from '@angular/core';
import {Router, RouterOutlet} from '@angular/router';
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
  isConnecting: boolean = false;
  isConnected: boolean = false;
  isLanded: boolean = false;

  constructor(
    private fb: FormBuilder,
    public droneService: DroneService,
    public router: Router
  ) {
    this.ipForm = this.fb.group({
      droneIp: ['', [Validators.required]]
    });
  }

  selectMode(mode: 'controlps' | 'controlkeyboard' | 'controltouch') {
    this.droneService.selectedMode = mode;
  }

  onDisconnect() {
    this.droneService.disconnect().subscribe({
      next: (res) => {
        console.log('Backend: Drohne erfolgreich getrennt', res);
        // Status erst bei Erfolg zurücksetzen
        this.isConnected = false;
        this.isConnecting = false;
        this.droneService.selectedMode = null; // Modus auch zurücksetzen
        this.ipForm.enable();
      },
      error: (err) => {
        console.error('Fehler beim Trennen:', err);
        // Optional: Trotz Fehler trennen, falls das Backend "tot" ist
        this.isConnected = false;
        this.ipForm.enable();
      }
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
          this.ipForm.reset();
          this.isConnected = true;  //Diese Zeile auskommentieren, wenn man es ohne Backend versuchen will
        }
      });
    }
  }

  // Diese Methode wird aufgerufen, wenn der Flug beendet wurde

  onDroneLanded() {

    this.isLanded = true;

// Setze Validator für den Kursnamen erst jetzt auf 'required'

    this.ipForm.get('courseName')?.setValidators([Validators.required]);

    this.ipForm.get('courseName')?.updateValueAndValidity();

  }



// Speichert den Flugkurs endgültig in der Datenbank

  saveFlightCourse() {

    if (this.ipForm.get('courseName')?.valid) {

      const payload = {

        ip: this.ipForm.value.droneIp,

        courseName: this.ipForm.value.courseName

      };



      console.log('Speichere Flugkurs in Datenbank:', payload);



// Hier rufen wir den Service auf

      this.droneService.saveFlight(payload).subscribe({

        next: (res) => {

          alert('Flugkurs erfolgreich gespeichert!');

          this.isLanded = false; // Feld wieder ausblenden

          this.ipForm.get('courseName')?.reset();

        },

        error: (err) => console.error('Fehler beim Speichern:', err)

      });

    }

  }

  onContinue() {
    if (this.droneService.selectedMode) {
      this.router.navigate(['/control']);
    }
  }
}
