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
  // Hier fehlte die Zuweisung und der richtige Typ
  isConnecting: boolean = false;

  constructor(
    private fb: FormBuilder,
    private droneService: DroneService,
    public router: Router
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
          this.router.navigate(['/control']);
        },
        error: (err) => {
          console.error('Verbindung fehlgeschlagen:', err);
          this.isConnecting = false;
          this.ipForm.reset();
          this.router.navigate(['/control']);   //Diese Zeile auskommentieren, wenn man es ohne Backend versuchen will
        }
      });
    }
  }
}
