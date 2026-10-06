import React from 'react';
import { Loader2, AlertCircle, Inbox } from 'lucide-react';

export function LoadingSpinner({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-slate-400 space-y-3">
      <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      <span className="text-sm font-medium tracking-wide">{message}</span>
    </div>
  );
}

export function ErrorMessage({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-lg bg-red-950/40 border border-red-900/60 p-4 text-red-200 space-y-3 my-4">
      <div className="flex items-start space-x-3">
        <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-red-300">Operational Error</h4>
          <p className="text-sm text-red-300/80 mt-1">{message}</p>
        </div>
      </div>
      {onRetry && (
        <div className="flex justify-end pt-1">
          <button
            onClick={onRetry}
            className="px-3 py-1.5 bg-red-900/40 hover:bg-red-800/60 text-xs font-medium text-red-200 rounded border border-red-700/60 transition"
          >
            Retry Request
          </button>
        </div>
      )}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-slate-800 rounded-lg bg-slate-900/30">
      <Inbox className="w-10 h-10 text-slate-600 mb-3" />
      <h3 className="text-base font-medium text-slate-300">{title}</h3>
      <p className="text-sm text-slate-500 max-w-md mt-1 mb-4">{description}</p>
      {action}
    </div>
  );
}
