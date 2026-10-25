import React, { useState } from 'react';
import { Terminal, Copy, Check } from 'lucide-react';

interface Props {
  logs: string[];
  title?: string;
  maxHeight?: string;
}

export const LogViewer: React.FC<Props> = ({
  logs,
  title = 'Execution Logs',
  maxHeight = 'max-h-96',
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(logs.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950 overflow-hidden shadow-md">
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-900 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-slate-400" />
          <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            {title}
          </span>
          <span className="text-[11px] text-slate-500">
            ({logs.length} lines)
          </span>
        </div>
        <button
          onClick={handleCopy}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded transition"
          title="Copy logs to clipboard"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span>Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      <div className={`p-4 overflow-y-auto font-mono text-xs text-slate-300 space-y-1 ${maxHeight}`}>
        {logs.length === 0 ? (
          <p className="text-slate-500 italic">No logs recorded yet.</p>
        ) : (
          logs.map((line, idx) => (
            <div key={idx} className="flex gap-3 hover:bg-slate-900/60 py-0.5 px-1 rounded">
              <span className="text-slate-600 select-none text-[11px] w-8 text-right shrink-0">
                {idx + 1}
              </span>
              <span className="break-all whitespace-pre-wrap">{line}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
