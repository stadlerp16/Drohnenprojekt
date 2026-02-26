import { Component, OnInit } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { NgIf } from '@angular/common';
import { Router } from '@angular/router';
import { DroneService } from '../app/services/drohne.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [ReactiveFormsModule, NgIf],
  templateUrl: './home.html',
  styleUrl: './home.css'
})
export class Home implements OnInit {

  ipForm: FormGroup;
  isConnecting = false;
  isConnected = false;
  isLanded = false;

  ngOnInit() {
    this.resetComponentState();
  }

  private resetComponentState() {
    this.isConnected = false;
    this.isConnecting = false;
    this.isLanded = false;
    this.ipForm.enable();
    this.ipForm.reset();
    this.droneService.selectedMode = null;
  }

  constructor(
    private fb: FormBuilder,
    public droneService: DroneService,
    public router: Router
  ) {
    this.ipForm = this.fb.group({
      droneIp: ['', Validators.required]
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
        this.droneService.selectedMode = null;
        // Modus auch zurücksetzen
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

      this.droneService.sendIpAddress(ip).subscribe({
        next: (response) => {
          this.isConnecting = false;
          this.isConnected = true;
        },
        error: () => {
          this.isConnecting = false;
          this.ipForm.reset();
          this.isConnected = true;
        }
      });
    }
  }

  onDroneLanded() {
    this.isLanded = true;
    this.ipForm.get('courseName')?.setValidators([Validators.required]);
    this.ipForm.get('courseName')?.updateValueAndValidity();
  }

  saveFlightCourse() {
    if (this.ipForm.get('courseName')?.valid) {
      const payload = {
        ip: this.ipForm.value.droneIp,
        courseName: this.ipForm.value.courseName
      };

      this.droneService.saveFlight(payload).subscribe(() => {
        this.isLanded = false;
        this.ipForm.get('courseName')?.reset();
      });
    }
  }
  onContinue() {
    if (this.droneService.selectedMode) {
      this.router.navigate(['/control']);
    }
  }
}


