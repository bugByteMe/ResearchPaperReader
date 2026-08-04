import { lazy, Suspense, useEffect, useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './auth';
import Layout from './components/Layout';

const loadLabelsPage = () => import('./pages/LabelsPage');
const loadKnowledgeBasePage = () => import('./pages/KnowledgeBasePage');
const loadLogsPage = () => import('./pages/LogsPage');
const loadPaperDetailPage = () => import('./pages/PaperDetailPage');
const loadPapersPage = () => import('./pages/PapersPage');
const loadPromptsPage = () => import('./pages/PromptsPage');
const loadSettingsPage = () => import('./pages/SettingsPage');
const loadMonthlyTrendsPage = () => import('./pages/MonthlyTrendsPage');
const loadSetupPage = () => import('./pages/SetupPage');

const LabelsPage = lazy(loadLabelsPage);
const KnowledgeBasePage = lazy(loadKnowledgeBasePage);
const LogsPage = lazy(loadLogsPage);
const PaperDetailPage = lazy(loadPaperDetailPage);
const PapersPage = lazy(loadPapersPage);
const PromptsPage = lazy(loadPromptsPage);
const SettingsPage = lazy(loadSettingsPage);
const MonthlyTrendsPage = lazy(loadMonthlyTrendsPage);
const SetupPage = lazy(loadSetupPage);

export default function App() {
  const [configured, setConfigured] = useState<boolean | null>(null);
  useEffect(() => {
    import('./api/client').then(({ api }) => api.getWorkspace().then((workspace) => setConfigured(Boolean(workspace?.is_configured))).catch(() => setConfigured(false)));
  }, []);

  return (
    <AuthProvider>
      <Suspense fallback={<div className="loadingPage">加载中...</div>}>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Navigate to={configured ? '/papers' : '/setup'} replace />} />
            <Route path="/setup" element={<SetupPage />} />
            <Route path="/papers" element={<PapersPage />} />
            <Route path="/daily" element={<Navigate to="/monthly" replace />} />
            <Route path="/monthly" element={<MonthlyTrendsPage />} />
            <Route path="/papers/:id" element={<PaperDetailPage />} />
            <Route path="/prompts" element={<PromptsPage />} />
            <Route path="/knowledge-base" element={<KnowledgeBasePage />} />
            <Route path="/logs" element={<LogsPage />} />
            <Route path="/labels" element={<LabelsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </Suspense>
    </AuthProvider>
  );
}
