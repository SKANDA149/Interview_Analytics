import React, { useState, useEffect } from 'react';
import { Navbar, NavTab } from './components/Navbar';
import { OverviewPage } from './pages/OverviewPage';
import { UploadPage } from './pages/UploadPage';
import { HistoryPage } from './pages/HistoryPage';
import { DetailsPage } from './pages/DetailsPage';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<NavTab>('overview');
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  // Sync state with simple URL hash for clean browser reload & bookmarking
  useEffect(() => {
    const parseHash = () => {
      const hash = window.location.hash.replace(/^#\/?/, '');
      if (hash.startsWith('details/')) {
        const id = hash.replace('details/', '');
        setSelectedJobId(id);
        setCurrentTab('details');
      } else if (hash === 'upload') {
        setCurrentTab('upload');
      } else if (hash === 'history') {
        setCurrentTab('history');
      } else {
        setCurrentTab('overview');
      }
    };

    parseHash();
    window.addEventListener('hashchange', parseHash);
    return () => window.removeEventListener('hashchange', parseHash);
  }, []);

  const navigateTo = (tab: NavTab, jobId?: string) => {
    if (tab === 'details' && jobId) {
      setSelectedJobId(jobId);
      window.location.hash = `#/details/${jobId}`;
    } else {
      setSelectedJobId(null);
      window.location.hash = `#/${tab}`;
    }
    setCurrentTab(tab);
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 antialiased selection:bg-blue-600 selection:text-white">
      {/* Navigation Header */}
      <Navbar
        currentTab={currentTab}
        onSelectTab={(tab) => navigateTo(tab)}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentTab === 'overview' && (
          <OverviewPage
            onStartUpload={() => navigateTo('upload')}
            onViewDetails={(jobId) => navigateTo('details', jobId)}
            onViewHistory={() => navigateTo('history')}
          />
        )}

        {currentTab === 'upload' && (
          <UploadPage
            onViewReport={(jobId) => navigateTo('details', jobId)}
          />
        )}

        {currentTab === 'history' && (
          <HistoryPage
            onViewReport={(jobId) => navigateTo('details', jobId)}
            onStartUpload={() => navigateTo('upload')}
          />
        )}

        {currentTab === 'details' && selectedJobId && (
          <DetailsPage
            jobId={selectedJobId}
            onBack={() => navigateTo('history')}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-center">
          <p className="font-mono text-[11px] text-slate-400">
            Local-First Edge Architecture • CPU-Only Offline Evaluation
          </p>
        </div>
      </footer>
    </div>
  );
};

export default App;
