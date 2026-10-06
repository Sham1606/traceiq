import React from 'react';
import { FileSpreadsheet, AlertCircle, FileText } from 'lucide-react';

export function PostmortemSection() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <FileSpreadsheet className="w-4 h-4 text-indigo-400" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
            Automated Postmortem Generation
          </h3>
        </div>
        <div className="text-[11px] font-mono text-amber-400 flex items-center space-x-1">
          <AlertCircle className="w-3.5 h-3.5" />
          <span>STATUS: PENDING (PHASE 5 BACKEND)</span>
        </div>
      </div>

      <div className="bg-slate-900/50 rounded-lg border border-slate-800 p-8 text-center space-y-4">
        <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 mx-auto">
          <FileText className="w-6 h-6" />
        </div>
        <div>
          <h4 className="text-sm font-semibold text-slate-200">
            Postmortem Generator Capability Pending
          </h4>
          <p className="text-xs text-slate-400 max-w-lg mx-auto mt-1 leading-relaxed">
            Automated postmortem documentation synthesis is planned for Phase 5 following live LLM agent orchestration. No postmortem data is fabricated.
          </p>
        </div>

        <div className="text-[11px] font-mono text-slate-500 bg-slate-950 max-w-md mx-auto p-3 rounded border border-slate-800 text-left">
          Planned Postmortem Schema:<br />
          • Executive Summary &amp; Impact Duration<br />
          • Verified Root Cause Analysis<br />
          • Supporting Evidence &amp; Causal Chains<br />
          • Recovery Action &amp; Simulation Results<br />
          • Action Items &amp; Architectural Follow-ups
        </div>
      </div>
    </div>
  );
}
