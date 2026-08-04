import { useEffect, useState } from 'react';
import { useAuth } from '../auth';
import { api, DailyRefreshRun } from '../api/client';

const statusText: Record<DailyRefreshRun['status'], string> = {
  running: '运行中',
  succeeded: '已完成',
  failed: '失败',
};

const triggerText: Record<DailyRefreshRun['trigger_type'], string> = {
  scheduled: '自动',
  manual: '手动',
};

function formatTime(value: string | null) {
  return value ? new Date(value).toLocaleString() : '-';
}

function formatWindow(run: DailyRefreshRun) {
  return run.date_from && run.date_to ? `${run.date_from} 至 ${run.date_to}` : '-';
}

function diagnosticText(run: DailyRefreshRun) {
  if (run.status === 'failed') return run.error_message || '-';
  if (!run.date_from && !run.date_to && run.matched === 0 && run.skipped_existing === 0) return '旧日志未记录检索诊断信息。';
  if (run.matched === 0 && run.imported === 0) return 'arXiv 未返回匹配论文，请检查日期窗口、关键词或分类。';
  if (run.imported === 0 && run.skipped_existing > 0) return `匹配 ${run.matched} 篇，其中 ${run.skipped_existing} 篇已存在，没有新导入。`;
  return `匹配 ${run.matched} 篇，已存在 ${run.skipped_existing} 篇，新导入 ${run.imported} 篇。`;
}

export default function LogsPage() {
  const { isAdmin } = useAuth();
  const [runs, setRuns] = useState<DailyRefreshRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = async (fresh = false) => {
    setError('');
    setLoading(true);
    try {
      setRuns(await api.listDailyRefreshRuns(fresh));
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  const runNow = async () => {
    setMessage('');
    setError('');
    setRunning(true);
    try {
      const result = await api.runScheduledRefresh();
      setMessage(`已导入 ${result.imported} 篇，已分析 ${result.analyzed} 篇`);
      await load(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : '任务失败');
      await load(true);
    } finally {
      setRunning(false);
    }
  };

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  return (
    <section>
      <div className="pageHeader">
        <div>
          <h1>任务日志</h1>
          <p>记录每日自动刷新和手动触发刷新是否完成、检索窗口、匹配数量、已存在数量、导入数量、分析数量和错误信息。</p>
        </div>
        <div className="headerActions">
          <button onClick={() => load(true)} disabled={loading}>{loading ? '刷新中...' : '刷新日志'}</button>
          {isAdmin && <button onClick={runNow} disabled={running}>{running ? '运行中...' : '立即运行每日任务'}</button>}
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      {message && <div className="success">{message}</div>}
      <div className="logTable">
        <div className="logRow logHeader">
          <span>触发</span>
          <span>状态</span>
          <span>开始时间</span>
          <span>完成时间</span>
          <span>检索窗口</span>
          <span>匹配/已有/导入</span>
          <span>分析</span>
          <span>诊断</span>
        </div>
        {runs.map((run) => (
          <div className="logRow" key={run.id}>
            <span>{triggerText[run.trigger_type] || run.trigger_type}</span>
            <span className={`statusBadge ${run.status}`}>{statusText[run.status] || run.status}</span>
            <span>{formatTime(run.started_at)}</span>
            <span>{formatTime(run.finished_at)}</span>
            <span>{formatWindow(run)}</span>
            <span>{run.matched} / {run.skipped_existing} / {run.imported}</span>
            <span>{run.analyzed}</span>
            <span className={run.status === 'failed' ? 'logError' : 'logDiagnostic'} title={`${run.query} ${run.categories} ${run.sort_by}/${run.sort_order}`}>
              {diagnosticText(run)}
            </span>
          </div>
        ))}
        {!runs.length && <div className="emptyState">暂无任务日志</div>}
      </div>
    </section>
  );
}
