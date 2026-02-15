import { Routes } from '@angular/router';
import { Dashboard } from '../dashboard/dashboard';

export const routes: Routes = [
  { path: 'control', component: Dashboard },
  { path: '', children: [] }, // Bleibt leer, damit App.html das Formular zeigt
  { path: '**', redirectTo: '' }
];
