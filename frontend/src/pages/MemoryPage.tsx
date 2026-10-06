import React from 'react';
import { History } from 'lucide-react';
import { HistoricalMemorySection } from '../features/investigation/HistoricalMemorySection';

export function MemoryPage() {
  return (
    <div className="space-y-6">
      <div className="pb-2 border-b border-slate-800">
        <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center space-x-2">
          <History className="w-5 h-5 text-indigo-400" />
          <span>Organizational Incident Memory</span>
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Search indexed historical incident fingerprints, verified root causes, and prior recovery resolutions.
        </p>
      </div>

      <HistoricalMemorySection initialFingerprint="" />
    </div>
  );
}
