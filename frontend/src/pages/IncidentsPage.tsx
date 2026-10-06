import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  Clock,
  ArrowRight,
  Filter,
  Search,
  Server,
  Layers,
  RefreshCw,
  Zap,
} from 'lucide-react';
import { api } from '../services/api';
import { IncidentResponse } from '../types/api';
import { SeverityBadge, StatusBadge } from '../components/common/Badge';
import { LoadingSpinner, ErrorMessage, EmptyState } from '../components/common/Feedback';

export function IncidentsPage() {
  const navigate = useNavigate();
  const [incidents, setIncidents] = useState<IncidentResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const fetchIncidents = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listIncidents(0, 100);
      setIncidents(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch incident directory');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
  }, []);

  const filteredIncidents = incidents.filter((inc) => {
    const matchesSearch =
      inc.title.toLowerCase().includes(search.toLowerCase()) ||
      inc.id.toLowerCase().includes(search.toLowerCase()) ||
      inc.scenario_id.toLowerCase().includes(search.toLowerCase()) ||
      inc.affected_services.some((s) => s.toLowerCase().includes(search.toLowerCase()));

    const matchesSeverity =
      severityFilter === 'all' || inc.severity.toLowerCase() === severityFilter.toLowerCase();
    const matchesStatus =
      statusFilter === 'all' || inc.status.toLowerCase() === statusFilter.toLowerCase();

    return matchesSearch && matchesSeverity && matchesStatus;
  });

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Intro */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center space-x-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            <span>Incident Directory</span>
            <span className="text-xs font-normal text-slate-400 px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700">
              {total} Total
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Active and archived production incidents available for deterministic evidence correlation.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={fetchIncidents}
            disabled={loading}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-medium bg-slate-900 border border-slate-700 hover:bg-slate-800 text-slate-300 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-3 bg-slate-900/60 p-3 rounded-lg border border-slate-800">
        <div className="md:col-span-6 relative">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by ID, title, service, or scenario..."
            className="w-full bg-slate-950 border border-slate-800 rounded pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="md:col-span-3 flex items-center space-x-2">
          <Filter className="w-3.5 h-3.5 text-slate-500 shrink-0" />
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Severities</option>
            <option value="sev1">SEV1 - Critical</option>
            <option value="sev2">SEV2 - High</option>
            <option value="sev3">SEV3 - Medium</option>
            <option value="sev4">SEV4 - Low</option>
          </select>
        </div>

        <div className="md:col-span-3 flex items-center space-x-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Statuses</option>
            <option value="detected">Detected</option>
            <option value="investigating">Investigating</option>
            <option value="mitigated">Mitigated</option>
            <option value="resolved">Resolved</option>
          </select>
        </div>
      </div>

      {/* Content State */}
      {loading ? (
        <LoadingSpinner message="Fetching incident records from backend..." />
      ) : error ? (
        <ErrorMessage message={error} onRetry={fetchIncidents} />
      ) : filteredIncidents.length === 0 ? (
        <EmptyState
          title="No Incidents Found"
          description={
            incidents.length === 0
              ? 'No incidents have been registered in the database yet. Use the backend test scenarios to populate incident telemetry.'
              : 'No incidents match your search and filter criteria.'
          }
        />
      ) : (
        <div className="border border-slate-800 rounded-lg overflow-hidden bg-slate-900/40">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Incident Details</th>
                  <th className="py-3 px-4">Scenario ID</th>
                  <th className="py-3 px-4">Affected Services</th>
                  <th className="py-3 px-4">Detected At</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Workspace</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {filteredIncidents.map((incident) => (
                  <tr
                    key={incident.id}
                    onClick={() => navigate(`/incidents/${incident.id}`)}
                    className="hover:bg-slate-800/40 cursor-pointer transition group"
                  >
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <SeverityBadge severity={incident.severity} />
                    </td>

                    <td className="py-3.5 px-4 font-sans">
                      <div className="font-semibold text-slate-200 group-hover:text-indigo-300 transition flex items-center space-x-1.5">
                        <span>{incident.title}</span>
                      </div>
                      <div className="text-[11px] font-mono text-slate-500 mt-0.5">
                        ID: {incident.id}
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-slate-400 font-mono text-xs">
                      {incident.scenario_id}
                    </td>

                    <td className="py-3.5 px-4 font-sans">
                      <div className="flex flex-wrap gap-1">
                        {incident.affected_services.map((svc) => (
                          <span
                            key={svc}
                            className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-300 border border-slate-700/60"
                          >
                            <Server className="w-2.5 h-2.5 mr-1 text-slate-400" />
                            {svc}
                          </span>
                        ))}
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-slate-400 text-xs whitespace-nowrap">
                      <div className="flex items-center space-x-1">
                        <Clock className="w-3 h-3 text-slate-500" />
                        <span>{formatDate(incident.detected_at)}</span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <StatusBadge status={incident.status} />
                    </td>

                    <td className="py-3.5 px-4 text-right whitespace-nowrap font-sans">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/incidents/${incident.id}`);
                        }}
                        className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-indigo-950/70 hover:bg-indigo-900 border border-indigo-800/80 text-indigo-300 text-xs font-medium transition"
                      >
                        <span>Investigate</span>
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
