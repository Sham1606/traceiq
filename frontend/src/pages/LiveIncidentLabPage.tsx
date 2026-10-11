import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  Play,
  Layers,
  Database,
  Activity,
  Server,
  FileCode,
  ShieldAlert,
  Clock,
  ArrowRight,
  RotateCcw,
  Plus,
  HelpCircle,
  AlertCircle,
} from 'lucide-react';
import { api } from '../services/api';
import { SeverityBadge } from '../components/common/Badge';

// Seven neutral telemetry inputs for the Live Incident Lab example.
const DEMO_ORDER_LATENCY_EVIDENCE = [
  {
    id: 'E-001',
    type: 'metric',
    service: 'orders-db',
    metric: 'cpu_utilization',
    timestamp: '2026-10-09T18:10:00Z',
    baseline: 42.0,
    incident: 42.0,
    value: 42.0,
    delta: 0.0,
    anomaly: false,
    summary: 'orders-db CPU utilization measured 42% at 18:10.',
  },
  {
    id: 'E-002',
    type: 'metric',
    service: 'orders-db',
    metric: 'cpu_utilization',
    timestamp: '2026-10-09T18:14:00Z',
    baseline: 42.0,
    incident: 91.0,
    value: 91.0,
    delta: 49.0,
    anomaly: true,
    summary: 'orders-db CPU utilization measured 91% at 18:14.',
  },
  {
    id: 'E-003',
    type: 'metric',
    service: 'orders-db',
    metric: 'connection_utilization',
    timestamp: '2026-10-09T18:15:00Z',
    baseline: 35.0,
    incident: 97.0,
    value: 97.0,
    delta: 62.0,
    anomaly: true,
    summary: 'orders-db connection utilization measured 97% at 18:15.',
  },
  {
    id: 'E-004',
    type: 'metric',
    service: 'order-service',
    metric: 'request_latency_ms',
    timestamp: '2026-10-09T18:16:00Z',
    baseline: 50.0,
    incident: 240.0,
    value: 240.0,
    delta: 190.0,
    delta_ratio: 3.8,
    anomaly: true,
    summary: 'order-service request latency increased 380% at 18:16.',
  },
  {
    id: 'E-005',
    type: 'metric',
    service: 'api-gateway',
    metric: 'http_5xx_rate',
    timestamp: '2026-10-09T18:17:00Z',
    baseline: 0.05,
    incident: 0.17,
    value: 0.17,
    delta: 0.12,
    delta_ratio: 2.4,
    anomaly: true,
    summary: 'api-gateway error rate increased 240% at 18:17.',
  },
  {
    id: 'E-006',
    type: 'deployment',
    service: 'order-service',
    event_id: 'dep-none',
    timestamp: '2026-10-09T18:18:00Z',
    summary: 'No deployment was reported during the observed incident window.',
  },
  {
    id: 'E-007',
    type: 'dependency',
    service: 'payment-provider-api',
    timestamp: '2026-10-09T18:18:00Z',
    summary: 'External dependency health was reported within normal operating range.',
  },
];

export function LiveIncidentLabPage() {
  const navigate = useNavigate();

  const [title, setTitle] = useState('Order Processing Latency');
  const [severity, setSeverity] = useState<'sev1' | 'sev2' | 'sev3' | 'sev4'>('sev1');
  const [servicesInput, setServicesInput] = useState('orders-db, order-service, api-gateway');
  const [description, setDescription] = useState(
    'Customers are experiencing slow order processing and intermittent order failures.'
  );
  const [detectedAt, setDetectedAt] = useState(new Date().toISOString().slice(0, 19));
  const [evidenceJson, setEvidenceJson] = useState(
    JSON.stringify(DEMO_ORDER_LATENCY_EVIDENCE, null, 2)
  );

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aiMode, setAiMode] = useState<'mock' | 'gemini' | 'deterministic' | 'unavailable'>('unavailable');

  useEffect(() => {
    let mounted = true;
    api.getHealth()
      .then((health) => {
        if (mounted) setAiMode(health.ai_mode);
      })
      .catch(() => {
        if (mounted) setAiMode('unavailable');
      });
    return () => {
      mounted = false;
    };
  }, []);

  const aiModeLabel = aiMode === 'mock'
    ? 'MOCK'
    : aiMode === 'gemini'
      ? 'GEMINI CONFIGURED · NOT VERIFIED'
      : aiMode === 'deterministic'
        ? 'DETERMINISTIC'
        : 'UNAVAILABLE / FALLBACK';

  // Quick preset loaders
  const loadOrderLatencyDemo = () => {
    setTitle('Order Processing Latency');
    setSeverity('sev1');
    setServicesInput('orders-db, order-service, api-gateway');
    setDescription(
      'Customers are experiencing slow order processing and intermittent order failures.'
    );
    setEvidenceJson(JSON.stringify(DEMO_ORDER_LATENCY_EVIDENCE, null, 2));
    setError(null);
  };

  const loadAuthFailureDemo = () => {
    setTitle('Authentication Service Token Verification Storm');
    setSeverity('sev1');
    setServicesInput('auth-service, api-gateway, redis-cache');
    setDescription('Public key rotation synchronization lag caused widespread 401 rejections.');
    const authEvidence = [
      {
        type: 'log',
        service: 'auth-service',
        event_type: 'InvalidSignatureException',
        count: 4820,
        error_or_warn_count: 4820,
        summary: '4,820 JWT signature verification rejections logged within 3 minutes of rotation.',
      },
      {
        type: 'metric',
        service: 'api-gateway',
        metric: 'http_401_ratio',
        baseline: 0.01,
        incident: 0.44,
        value: 0.44,
        delta: 0.43,
        anomaly: true,
        summary: 'API Gateway 401 Unauthorized responses surged to 44% of total traffic.',
      },
      {
        type: 'configuration',
        service: 'auth-service',
        summary: 'JWKS endpoint public key cache TTL updated from 3600s to 60s.',
      },
    ];
    setEvidenceJson(JSON.stringify(authEvidence, null, 2));
    setError(null);
  };

  const handleStartInvestigation = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    let parsedEvidence: any[];
    try {
      parsedEvidence = JSON.parse(evidenceJson);
      if (!Array.isArray(parsedEvidence)) {
        throw new Error('Evidence input must be a JSON array of telemetry/event objects.');
      }
    } catch (err: any) {
      setError(`Invalid JSON Evidence: ${err.message}`);
      return;
    }

    const services = servicesInput
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    setSubmitting(true);
    try {
      // 1. Create live custom incident
      const newIncident = await api.createLiveIncident({
        title,
        severity,
        affected_services: services,
        description,
        detected_at: new Date(detectedAt).toISOString(),
        evidence_items: parsedEvidence,
      });

      // 2. Automatically launch investigation pipeline on the custom evidence
      await api.startInvestigation(newIncident.id);

      // 3. Immediately transition presenter to live Workspace
      navigate(`/incidents/${newIncident.id}`);
    } catch (err: any) {
      setError(err instanceof Error ? err.message : 'Failed to launch live investigation');
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Banner / Header */}
      <div className="bg-slate-900/90 rounded-lg border border-slate-800 p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 p-6 opacity-10 pointer-events-none">
          <Sparkles className="w-36 h-36 text-indigo-400" />
        </div>

        <div className="space-y-2 relative">
          <div className="flex items-center space-x-2 text-indigo-400">
            <Sparkles className="w-5 h-5" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider">
              TRACEIQ Live Lab
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            Live Incident Lab
          </h1>
          <p className="text-sm text-slate-300 max-w-2xl">
            Create an incident with supplied telemetry and run the configured TRACEIQ investigation pipeline. No canonical scenario ground truth is attached; results are based on the supplied evidence.
          </p>
          <div role="status" aria-label="AI mode" className="inline-flex rounded border border-slate-700 bg-slate-950 px-2.5 py-1 text-[11px] font-mono font-semibold text-slate-200">
            AI MODE: {aiModeLabel}
          </div>
        </div>

        {/* Demo Templates Bar */}
        <div className="mt-5 pt-4 border-t border-slate-800/80 flex flex-wrap items-center gap-2">
          <span className="text-xs font-mono text-slate-400">Judge / Presenter Presets:</span>
          <button
            type="button"
            onClick={loadOrderLatencyDemo}
            className="px-2.5 py-1 rounded text-xs font-medium bg-indigo-950/80 hover:bg-indigo-900 text-indigo-300 border border-indigo-800 transition"
          >
            Order Processing Latency (SEV1)
          </button>
          <button
            type="button"
            onClick={loadAuthFailureDemo}
            className="px-2.5 py-1 rounded text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
          >
            Auth Token Storm (SEV1)
          </button>
        </div>
      </div>

      {/* Form Card */}
      <form onSubmit={handleStartInvestigation} className="bg-slate-900/60 rounded-lg border border-slate-800 p-6 space-y-5">
        {error && (
          <div className="p-3 rounded bg-rose-950/70 border border-rose-800 text-rose-300 text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Incident Title */}
        <div className="space-y-1.5">
          <label className="block text-xs font-semibold text-slate-200 uppercase tracking-wider font-mono">
            Incident Title
          </label>
          <input
            type="text"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Order Processing Latency"
            className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* Severity & Detected Time Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-slate-200 uppercase tracking-wider font-mono">
              Severity Level
            </label>
            <div className="grid grid-cols-4 gap-2">
              {(['sev1', 'sev2', 'sev3', 'sev4'] as const).map((lvl) => (
                <button
                  key={lvl}
                  type="button"
                  onClick={() => setSeverity(lvl)}
                  className={`py-1.5 text-xs font-bold rounded font-mono uppercase transition border ${
                    severity === lvl
                      ? lvl === 'sev1'
                        ? 'bg-rose-950 text-rose-200 border-rose-700'
                        : lvl === 'sev2'
                        ? 'bg-amber-950 text-amber-200 border-amber-700'
                        : 'bg-indigo-950 text-indigo-200 border-indigo-700'
                      : 'bg-slate-950 text-slate-400 border-slate-800 hover:bg-slate-800'
                  }`}
                >
                  {lvl.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-slate-200 uppercase tracking-wider font-mono">
              Detected Timestamp
            </label>
            <div className="relative">
              <Clock className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                required
                value={detectedAt}
                onChange={(e) => setDetectedAt(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded pl-9 pr-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>
        </div>

        {/* Affected Services */}
        <div className="space-y-1.5">
          <label className="block text-xs font-semibold text-slate-200 uppercase tracking-wider font-mono">
            Affected Services (comma separated)
          </label>
          <div className="relative">
            <Server className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              required
              value={servicesInput}
              onChange={(e) => setServicesInput(e.target.value)}
              placeholder="order-service, api-gateway, orders-db"
              className="w-full bg-slate-950 border border-slate-800 rounded pl-9 pr-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Description */}
        <div className="space-y-1.5">
          <label className="block text-xs font-semibold text-slate-200 uppercase tracking-wider font-mono">
            Incident Description
          </label>
          <textarea
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the observed system symptom..."
            className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* Structured Evidence Payload Input */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="block text-xs font-semibold text-slate-200 uppercase tracking-wider font-mono flex items-center space-x-1.5">
              <FileCode className="w-3.5 h-3.5 text-indigo-400" />
              <span>Evidence Input (Structured Telemetry JSON)</span>
            </label>
            <span className="text-[11px] font-mono text-slate-500">
              Metrics, Logs, Deployments, Dependencies
            </span>
          </div>

          <textarea
            rows={10}
            required
            aria-label="Evidence Input (Structured Telemetry JSON)"
            value={evidenceJson}
            onChange={(e) => setEvidenceJson(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded p-3 text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500 leading-relaxed"
          />
        </div>

        {/* Ground Truth Safety Firewall Assurance */}
        <div className="p-3 rounded bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-400 space-y-1">
          <div className="flex items-center space-x-2 text-emerald-400 font-semibold">
            <span>✓ GROUND TRUTH FIREWALL: ACTIVE</span>
          </div>
          <p className="text-slate-500">
            Custom incidents have no canonical scenario ground truth attached. Investigation findings are based on the evidence supplied above.
          </p>
        </div>

        {/* Action Button */}
        <div className="pt-2 flex items-center justify-end">
          <button
            type="submit"
            disabled={submitting}
            className={`inline-flex items-center space-x-2 px-6 py-2.5 rounded font-semibold text-sm shadow-lg transition ${
              submitting
                ? 'bg-indigo-900 text-indigo-300 cursor-wait'
                : 'bg-indigo-600 hover:bg-indigo-500 text-white'
            }`}
          >
            {submitting ? (
              <>
                <RotateCcw className="w-4 h-4 animate-spin" />
                <span>Launching Investigation...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                <span>START INVESTIGATION</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
