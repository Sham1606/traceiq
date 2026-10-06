import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { IncidentsPage } from './pages/IncidentsPage';
import { WorkspacePage } from './pages/WorkspacePage';
import { MemoryPage } from './pages/MemoryPage';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<Navigate to="/incidents" replace />} />
          <Route path="/incidents" element={<IncidentsPage />} />
          <Route path="/incidents/:incidentId" element={<WorkspacePage />} />
          <Route path="/memory" element={<MemoryPage />} />
          <Route path="*" element={<Navigate to="/incidents" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
