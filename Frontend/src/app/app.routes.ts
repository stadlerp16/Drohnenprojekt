import { Routes } from '@angular/router';
import { Dashboard } from '../dashboard/dashboard';
import { Home } from '../home/home';

export const routes: Routes = [
  { path: '', component: Home },
  { path: 'control', component: Dashboard },
  //{ path: '', children: [] }, // Bleibt leer, damit App.html das Formular zeigt
  { path: '**', redirectTo: '' }
];
