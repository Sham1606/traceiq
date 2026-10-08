import { Check, Circle, LoaderCircle } from 'lucide-react';
import { InvestigationResponse } from '../../types/api';

interface InvestigationProgressProps {
  investigation: InvestigationResponse | null;
  running: boolean;
  elapsedSeconds?: number | null;
}

type StageState = 'complete' | 'pending' | 'not-reported' | 'failed';

interface Stage {
  label: string;
  state: StageState;
}

function formatElapsed(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return minutes > 0 ? `${minutes}m ${remainingSeconds}s` : `${remainingSeconds}s`;
}

export function InvestigationProgress({ investigation, running, elapsedSeconds }: InvestigationProgressProps) {
  const evidence = investigation?.evidence;
  const complete = investigation?.status === 'complete';
  const failed = investigation?.status === 'failed';
  const findings = evidence?.investigator_findings || [];

  const reported = (isReported: boolean): StageState => {
    if (isReported) return 'complete';
    if (failed) return 'failed';
    return complete ? 'not-reported' : 'pending';
  };
  const domainReported = (domain: string) => findings.some(
    (finding) => finding.investigator_type?.toLowerCase() === domain || finding.domain?.toLowerCase() === domain
  );

  const stages: Stage[] = [
    { label: 'Investigation started', state: running || !!investigation ? 'complete' : 'pending' },
    { label: 'Planning investigation', state: reported(!!evidence?.plan) },
    { label: 'Application analysis', state: reported(domainReported('application')) },
    { label: 'Database analysis', state: reported(domainReported('database')) },
    { label: 'Deployment analysis', state: reported(domainReported('deployment')) },
    { label: 'Dependency analysis', state: reported(domainReported('dependency')) },
    {
      label: 'Correlating evidence',
      state: reported(Array.isArray(evidence?.correlations) || Array.isArray(evidence?.correlation_findings)),
    },
    { label: 'Generating hypotheses', state: reported(Array.isArray(investigation?.hypotheses)) },
    { label: 'Challenging leading hypothesis', state: reported(!!investigation?.challenge) },
    {
      label: 'Validating results',
      state: reported(evidence?.ai_telemetry?.deterministic_validation === 'PASS'),
    },
    { label: 'Investigation complete', state: complete ? 'complete' : failed ? 'failed' : 'pending' },
  ];
  const completedCount = stages.filter((stage) => stage.state === 'complete').length;
  const evidenceCount = evidence?.evidence?.length ?? 0;
  const hypothesisCount = investigation?.hypotheses?.length ?? 0;

  const statusLabel = running
    ? 'Request in progress'
    : complete
      ? 'Complete'
      : failed
        ? 'Failed'
        : 'Not started';

  return (
    <section aria-label="Investigation progress" className="space-y-3 rounded-lg border border-slate-800 bg-slate-900/70 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div>
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">Investigation Progress</h2>
          <p className="mt-1 text-[11px] text-slate-500">
            Pipeline status comes from returned results; backend stage events are not streamed.
          </p>
        </div>
        <div className="flex items-center gap-3 text-[11px] font-mono">
          <span className={running ? 'text-amber-300' : complete ? 'text-emerald-300' : failed ? 'text-rose-300' : 'text-slate-400'}>
            {running && <LoaderCircle aria-hidden="true" className="mr-1 inline h-3 w-3 animate-spin" />}
            {statusLabel}
          </span>
          {elapsedSeconds != null && (
            <span className="text-slate-400">Elapsed {formatElapsed(elapsedSeconds)}</span>
          )}
          {!running && investigation && (
            <span className="text-slate-500">{completedCount}/{stages.length} reported</span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {stages.map((stage, index) => (
          <div key={stage.label} className="flex min-w-0 items-center gap-2 rounded border border-slate-800 bg-slate-950/60 px-2.5 py-2">
            {stage.state === 'complete' ? (
              <Check aria-hidden="true" className="h-3.5 w-3.5 shrink-0 text-emerald-400" />
            ) : (
              <Circle aria-hidden="true" className={`h-3.5 w-3.5 shrink-0 ${stage.state === 'failed' ? 'text-rose-400' : 'text-slate-600'}`} />
            )}
            <span className="min-w-0 flex-1 truncate text-[11px] text-slate-300">{stage.label}</span>
            <span className="shrink-0 text-[9px] uppercase text-slate-500">
              {stage.state === 'complete' ? 'Complete' : stage.state === 'failed' ? 'Failed' : stage.state === 'not-reported' ? 'Not reported' : running ? 'Awaiting response' : 'Pending'}
            </span>
          </div>
        ))}
      </div>

      {!running && investigation && (
        <p className="text-[11px] font-mono text-slate-400">
          Evidence items: {evidenceCount} · Hypotheses: {hypothesisCount} · Challenge: {investigation.challenge ? 'Completed' : 'Not reported'}
        </p>
      )}
    </section>
  );
}
