import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { Activity, UploadCloud, History, LayoutDashboard, Cpu } from 'lucide-react';

export type NavTab = 'overview' | 'upload' | 'history' | 'details';

interface Props {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
}

export const Navbar: React.FC<Props> = ({ currentTab, onSelectTab }) => {
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;
    const check = async () => {
      try {
        const res = await apiClient.checkHealth();
        if (mounted) setApiOnline(res.status === 'ok');
      } catch {
        if (mounted) setApiOnline(false);
      }
    };

    check();
    const interval = setInterval(check, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="sticky top-0 z-40 bg-white/95 dark:bg-slate-900/95 backdrop-blur border-b border-slate-200 dark:border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Project Title */}
          <div
            onClick={() => onSelectTab('overview')}
            className="flex items-center gap-3 cursor-pointer group"
          >
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-sm shadow-blue-500/20 group-hover:bg-blue-700 transition">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-900 dark:text-white tracking-tight text-lg">
                  Interview Analytics
                </span>
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                  <Cpu className="w-3 h-3" /> Edge CPU
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Offline Multimedia Analysis Studio
              </p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex items-center gap-1 sm:gap-2">
            <button
              onClick={() => onSelectTab('overview')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition ${
                currentTab === 'overview'
                  ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300'
                  : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Overview</span>
            </button>

            <button
              onClick={() => onSelectTab('upload')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition ${
                currentTab === 'upload'
                  ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300'
                  : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              <UploadCloud className="w-4 h-4" />
              <span>New Analysis</span>
            </button>

            <button
              onClick={() => onSelectTab('history')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition ${
                currentTab === 'history'
                  ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300'
                  : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              <History className="w-4 h-4" />
              <span>History</span>
            </button>
          </nav>

          {/* API Health Status Indicator */}
          <div className="flex items-center gap-2 pl-3 border-l border-slate-200 dark:border-slate-800">
            <div
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border"
              title={`FastAPI Server: ${apiClient.getBaseUrl()}`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  apiOnline === true
                    ? 'bg-emerald-500 animate-pulse'
                    : apiOnline === false
                    ? 'bg-rose-500'
                    : 'bg-amber-400'
                }`}
              />
              <span className="text-slate-700 dark:text-slate-300 hidden sm:inline">
                {apiOnline === true ? 'API Connected' : apiOnline === false ? 'API Offline' : 'Connecting...'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
