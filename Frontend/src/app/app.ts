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

  constructor(
    private fb: FormBuilder,
    public droneService: DroneService,
    public router: Router
  ) {
    this.ipForm = this.fb.group({
      droneIp: ['', [Validators.required]]
    });
  }

  selectMode(mode: 'keyboard' | 'controller') {
    this.droneService.selectedMode = mode;
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
  onContinue() {
    if (this.droneService.selectedMode) {
      this.router.navigate(['/control']);
    }
  }
}
