import { Routes } from '@angular/router';
import {Dashboard} from '../dashboard/dashboard';

export const routes: Routes = [
  { path: '', children: [] },
  { path: 'control', component: Dashboard }
];
