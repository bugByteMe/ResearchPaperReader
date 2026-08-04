import { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { api, WorkspaceSetup } from '../api/client';
import { useAuth } from '../auth';

const initialSetup: WorkspaceSetup = {
  name: '', description: '', analysis_language: 'Chinese', arxiv_query: '', arxiv_categories: '',
  arxiv_daily_lookback_days: 3, arxiv_max_results: 30, arxiv_sort_by: 'submitted_date', arxiv_sort_order: 'descending',
  knowledge_base_auto_update_enabled: false, knowledge_base: '', labels: [],
};

export default function SetupPage() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(initialSetup);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  if (!isAdmin) return <section><h1>初始化工作区</h1><p className="meta">请先使用侧栏中的管理员密码登录，再创建本地研究工作区。</p></section>;

  const update = <K extends keyof WorkspaceSetup>(key: K, value: WorkspaceSetup[K]) => setForm((current) => ({ ...current, [key]: value }));
  const submit = async () => {
    setError(''); setSaving(true);
    try { await api.setupWorkspace(form); navigate('/papers', { replace: true }); }
    catch (err) { setError(err instanceof Error ? err.message : '初始化失败'); }
    finally { setSaving(false); }
  };
  return <section>
    <h1>创建研究工作区</h1>
    <p className="meta">工作区定义论文筛选范围。所有默认 Prompt、标签和知识库均为通用模板，不会限制到特定领域。</p>
    {error && <div className="error">{error}</div>}
    <div className="panel settingsGrid">
      <label>工作区名称<input value={form.name} onChange={(e) => update('name', e.target.value)} placeholder="例如：LLM 安全研究" /></label>
      <label>分析输出语言<input value={form.analysis_language} onChange={(e) => update('analysis_language', e.target.value)} placeholder="Chinese" /></label>
      <label className="wide">研究范围说明<textarea value={form.description} onChange={(e) => update('description', e.target.value)} placeholder="说明应纳入和排除的研究主题。" /></label>
      <label className="wide">arXiv 查询<input value={form.arxiv_query} onChange={(e) => update('arxiv_query', e.target.value)} placeholder="例如：large language model safety" /></label>
      <label>arXiv 分类，可留空<input value={form.arxiv_categories} onChange={(e) => update('arxiv_categories', e.target.value)} placeholder="例如：cs.CL,cs.AI" /></label>
      <label>最大结果数<input type="number" min="1" max="100" value={form.arxiv_max_results} onChange={(e) => update('arxiv_max_results', Number(e.target.value))} /></label>
      <label>每日回溯天数<input type="number" min="1" max="30" value={form.arxiv_daily_lookback_days} onChange={(e) => update('arxiv_daily_lookback_days', Number(e.target.value))} /></label>
      <label>排序字段<select value={form.arxiv_sort_by} onChange={(e) => update('arxiv_sort_by', e.target.value as WorkspaceSetup['arxiv_sort_by'])}><option value="submitted_date">提交时间</option><option value="last_updated_date">更新时间</option><option value="relevance">相关性</option></select></label>
      <label>排序顺序<select value={form.arxiv_sort_order} onChange={(e) => update('arxiv_sort_order', e.target.value as WorkspaceSetup['arxiv_sort_order'])}><option value="descending">降序</option><option value="ascending">升序</option></select></label>
      <label className="wide">初始知识库，可留空<textarea value={form.knowledge_base} onChange={(e) => update('knowledge_base', e.target.value)} placeholder="可选：领域术语、分类和已知技术路线。" /></label>
    </div>
    <button disabled={saving || !form.name.trim() || !form.arxiv_query.trim()} onClick={submit}>{saving ? '初始化中...' : '创建工作区'}</button>
  </section>;
}
