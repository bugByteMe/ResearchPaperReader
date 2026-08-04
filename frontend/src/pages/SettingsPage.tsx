import { useEffect, useState } from 'react';
import { useAuth } from '../auth';
import { api, Workspace } from '../api/client';

export default function SettingsPage() {
  const { isAdmin } = useAuth();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  useEffect(() => { api.getWorkspace().then(setWorkspace).catch((err) => setError(err.message)); }, []);
  if (!workspace) return <section><h1>设置</h1><p className="meta">尚未初始化工作区。</p></section>;
  const update = <K extends keyof Workspace>(key: K, value: Workspace[K]) => setWorkspace((current) => current ? { ...current, [key]: value } : current);
  const save = async () => {
    setError(''); setMessage('');
    try {
      const { id, is_configured, ...payload } = workspace;
      void id; void is_configured;
      setWorkspace(await api.updateWorkspace(payload)); setMessage('已保存工作区配置');
    } catch (err) { setError(err instanceof Error ? err.message : '保存失败'); }
  };
  const run = async () => {
    setError(''); setMessage('');
    try { const result = await api.runScheduledRefresh(); setMessage(result.message); }
    catch (err) { setError(err instanceof Error ? err.message : '任务提交失败'); }
  };
  return <section>
    <h1>工作区设置</h1>
    {error && <div className="error">{error}</div>}{message && <div className="success">{message}</div>}
    <div className="panel settingsGrid">
      <label>名称<input readOnly={!isAdmin} value={workspace.name} onChange={(e) => update('name', e.target.value)} /></label>
      <label>分析语言<input readOnly={!isAdmin} value={workspace.analysis_language} onChange={(e) => update('analysis_language', e.target.value)} /></label>
      <label className="wide">研究范围<textarea readOnly={!isAdmin} value={workspace.description} onChange={(e) => update('description', e.target.value)} /></label>
      <label className="wide">arXiv 查询<input readOnly={!isAdmin} value={workspace.arxiv_query} onChange={(e) => update('arxiv_query', e.target.value)} /></label>
      <label>arXiv 分类<input readOnly={!isAdmin} value={workspace.arxiv_categories} onChange={(e) => update('arxiv_categories', e.target.value)} placeholder="可留空" /></label>
      <label>最大结果数<input readOnly={!isAdmin} type="number" min="1" max="100" value={workspace.arxiv_max_results} onChange={(e) => update('arxiv_max_results', Number(e.target.value))} /></label>
      <label>每日回溯天数<input readOnly={!isAdmin} type="number" min="1" max="30" value={workspace.arxiv_daily_lookback_days} onChange={(e) => update('arxiv_daily_lookback_days', Number(e.target.value))} /></label>
      <label>排序字段<select disabled={!isAdmin} value={workspace.arxiv_sort_by} onChange={(e) => update('arxiv_sort_by', e.target.value as Workspace['arxiv_sort_by'])}><option value="submitted_date">提交时间</option><option value="last_updated_date">更新时间</option><option value="relevance">相关性</option></select></label>
      <label>排序顺序<select disabled={!isAdmin} value={workspace.arxiv_sort_order} onChange={(e) => update('arxiv_sort_order', e.target.value as Workspace['arxiv_sort_order'])}><option value="descending">降序</option><option value="ascending">升序</option></select></label>
    </div>
    {isAdmin && <button onClick={save}>保存</button>}
    <div className="panel"><h2>刷新任务</h2><p>刷新任务会进入本地后台队列，由独立 worker 执行，不会阻塞浏览器请求。</p>{isAdmin && <button onClick={run}>提交立即刷新</button>}</div>
  </section>;
}
