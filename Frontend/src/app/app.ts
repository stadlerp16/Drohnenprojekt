import { Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { NgIf } from '@angular/common';
import { DroneService } from './services/drohne.service';

@Component({
  selector: 'app-root',
  standalone: true, // Sicherstellen, dass standalone aktiv ist
  imports: [RouterOutlet, ReactiveFormsModule, NgIf],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected readonly title = signal('SYPProjekt');

  ipForm: FormGroup;

  constructor(
    private fb: FormBuilder,
    private droneService: DroneService
  ) {
    this.ipForm = this.fb.group({
      droneIp: ['', [Validators.required]]
    });
  }

  onSubmit() {
    if (this.ipForm.valid) {
      const ip = this.ipForm.value.droneIp;
      console.log('Sende IP an Backend:', ip);

      // Aufruf des Services
      this.droneService.sendIpAddress(ip).subscribe({
        next: (response) => {
          console.log('Erfolgreich übertragen:', response);
        },
        error: (err) => {
          console.error('Fehler bei der Übertragung:', err);
        }
      });
    }
  }
}
