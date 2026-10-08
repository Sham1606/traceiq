import React, { useEffect, useState } from 'react';
import { Link, useLocation, Outlet } from 'react-router-dom';
import {
  ShieldAlert,
  Activity,
  History,
  FileSpreadsheet,
  Layers,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
} from 'lucide-react';
import { api } from '../../services/api';
import { HealthResponse } from '../../types/api';

export function AppShell() {
  const location = useLocation();
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    let mounted = true;
    const checkHealth = async () => {
      try {
        const res = await api.getHealth();
        if (mounted) setHealth(res);
      } catch {
        if (mounted) setHealth({ status: 'degraded', version: '0.1.0', db: 'error' });
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const isWorkspace = location.pathname.includes('/incidents/') && location.pathname.split('/').length > 2;
  const currentIncidentId = isWorkspace ? location.pathname.split('/')[2] : null;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Application Header */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <div className="flex items-center space-x-6">
            <Link to="/incidents" className="flex items-center space-x-2.5 group">
              <div className="w-8 h-8 rounded bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400 group-hover:bg-indigo-600/30 transition">
                <ShieldAlert className="w-5 h-5 text-indigo-400" />
              </div>
              <div className="flex flex-col">
                <span className="font-bold tracking-tight text-base text-slate-100 flex items-center space-x-1.5">
                  <span>TRACEIQ</span>
                  <span className="text-[10px] font-mono font-medium px-1.5 py-0.2 bg-indigo-950 text-indigo-300 rounded border border-indigo-800">
                    CORE
                  </span>
                </span>
                <span className="text-[10px] font-medium text-slate-400 tracking-wide uppercase">
                  Incident Investigation Workspace
                </span>
              </div>
            </Link>

            <nav className="hidden md:flex items-center space-x-1 pl-4 border-l border-slate-800">
              <Link
                to="/incidents"
                className={`px-3 py-1.5 rounded text-xs font-medium transition ${
                  location.pathname === '/' || location.pathname === '/incidents'
                    ? 'bg-slate-800 text-slate-100'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <div className="flex items-center space-x-1.5">
                  <Layers className="w-3.5 h-3.5" />
                  <span>Incidents</span>
                </div>
              </Link>

              <Link
                to="/lab"
                className={`px-3 py-1.5 rounded text-xs font-medium transition ${
                  location.pathname === '/lab'
                    ? 'bg-indigo-950/80 text-indigo-300 border border-indigo-700/80'
                    : 'text-indigo-400 hover:text-indigo-200 hover:bg-indigo-950/30'
                }`}
              >
                <div className="flex items-center space-x-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                  <span className="font-semibold">Live Incident Lab</span>
                </div>
              </Link>

              {currentIncidentId && (
                <Link
                  to={`/incidents/${currentIncidentId}`}
                  className={`px-3 py-1.5 rounded text-xs font-medium transition ${
                    isWorkspace
                      ? 'bg-indigo-950/60 text-indigo-300 border border-indigo-800/60'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <div className="flex items-center space-x-1.5">
                    <Activity className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Workspace ({currentIncidentId.slice(0, 8)})</span>
                  </div>
                </Link>
              )}

              <Link
                to="/memory"
                className={`px-3 py-1.5 rounded text-xs font-medium transition ${
                  location.pathname === '/memory'
                    ? 'bg-slate-800 text-slate-100'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <div className="flex items-center space-x-1.5">
                  <History className="w-3.5 h-3.5" />
                  <span>Historical Memory</span>
                </div>
              </Link>
            </nav>
          </div>

          {/* System status & telemetry indicators */}
          <div className="flex items-center space-x-4">
            <div className="hidden sm:flex items-center space-x-2 text-xs bg-slate-950/80 px-2.5 py-1 rounded border border-slate-800">
              <div className="flex items-center space-x-1.5">
                <span className="text-slate-400">Backend:</span>
                {health?.status === 'ok' ? (
                  <span className="flex items-center text-emerald-400 font-mono text-[11px]">
                    <CheckCircle2 className="w-3 h-3 mr-1" /> OK
                  </span>
                ) : (
                  <span className="flex items-center text-amber-400 font-mono text-[11px]">
                    <AlertTriangle className="w-3 h-3 mr-1" /> {health?.status || 'OFFLINE'}
                  </span>
                )}
              </div>
              <span className="text-slate-700">|</span>
              <div className="flex items-center space-x-1.5">
                <span className="text-slate-400">DB:</span>
                <span
                  className={`font-mono text-[11px] ${
                    health?.db === 'ok' ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {health?.db || 'OFFLINE'}
                </span>
              </div>
            </div>

            <div className="text-[11px] font-mono text-slate-500 hidden lg:block">
              ENGINE: DETERMINISTIC
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Outlet />
      </main>

      {/* Enterprise Status Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950 text-slate-500 text-xs py-3 px-4">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center space-x-3">
            <span className="font-semibold text-slate-400">TRACEIQ Investigation Core</span>
            <span>•</span>
            <span>Deterministic Evidence Engine</span>
            <span>•</span>
            <span>Phase 4 Enterprise Workspace</span>
          </div>
          <div className="text-[11px] text-slate-600 font-mono">
            Ground Truth Protected • Deterministic Analysis
          </div>
        </div>
      </footer>
    </div>
  );
}
