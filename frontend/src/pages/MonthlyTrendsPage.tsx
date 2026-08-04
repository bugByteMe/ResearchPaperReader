import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth';
import { api, MonthlyTrend, MonthlyTrends, PaperListItem } from '../api/client';

function formatDate(value: string) {
  return value ? value.slice(0, 10) : '日期未知';
}

function PaperCard({ paper }: { paper: PaperListItem }) {
  return (
    <article className="compactPaperCard">
      <div className="cardTopLine">
        <span className="dateText">{formatDate(paper.published_date || paper.created_at)}</span>
        <span className="chip">{paper.is_quality ? '优质论文' : '已入库'}</span>
      </div>
      <h2><Link to={`/papers/${paper.id}`}>{paper.title}</Link></h2>
      <div className="chipRow">
        {paper.labels.length ? paper.labels.map((item) => (
          <span className="chip" key={item.id}>{item.label.name}</span>
        )) : <span className="emptyChip">暂无标签</span>}
      </div>
      <div className="meta">作者：{paper.authors || '未知'}</div>
    </article>
  );
}

function PaperRow({ paper }: { paper: PaperListItem }) {
  return (
    <div className="paperListRow">
      <span className="dateText">{formatDate(paper.published_date || paper.created_at)}</span>
      <Link to={`/papers/${paper.id}`}>{paper.title}</Link>
      <span>{paper.is_quality ? '优质' : '入库'}</span>
      <span>{paper.labels.map((item) => item.label.name).join('、') || '暂无标签'}</span>
    </div>
  );
}

export default function MonthlyTrendsPage() {
  const { isAdmin } = useAuth();
  const [data, setData] = useState<MonthlyTrends | null>(null);
  const [paperLibrary, setPaperLibrary] = useState<PaperListItem[]>([]);
  const [viewMode, setViewMode] = useState<'list' | 'cards'>('list');
  const [loading, setLoading] = useState(false);
  const [paperLibraryLoading, setPaperLibraryLoading] = useState(false);
  const [editingTrendId, setEditingTrendId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editSummary, setEditSummary] = useState('');
  const [addingTrendId, setAddingTrendId] = useState<number | null>(null);
  const [expandedTrendIds, setExpandedTrendIds] = useState<number[]>([]);
  const [selectedPaperByTrend, setSelectedPaperByTrend] = useState<Record<number, string>>({});
  const [paperQueryByTrend, setPaperQueryByTrend] = useState<Record<number, string>>({});
  const [busyAction, setBusyAction] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [paperLibraryError, setPaperLibraryError] = useState('');

  const load = async (fresh = false) => {
    setError('');
    setLoading(true);
    try {
      setData(await api.listMonthlyTrends(fresh));
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load().catch((err) => setError(err.message));
    setPaperLibraryLoading(true);
    api.listPapers()
      .then(setPaperLibrary)
      .catch((err) => setPaperLibraryError(err instanceof Error ? err.message : '论文库加载失败'))
      .finally(() => setPaperLibraryLoading(false));
  }, []);

  const startEdit = (trend: MonthlyTrend) => {
    setMessage('');
    setError('');
    setEditingTrendId(trend.id);
    setEditTitle(trend.title);
    setEditSummary(trend.summary);
    setExpandedTrendIds((current) => current.includes(trend.id) ? current : [...current, trend.id]);
  };

  const saveTrend = async (trendId: number) => {
    setMessage('');
    setError('');
    setBusyAction(`save-${trendId}`);
    try {
      setData(await api.updateMonthlyTrend(trendId, { title: editTitle, summary: editSummary }));
      setEditingTrendId(null);
      setMessage('趋势已保存');
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存趋势失败');
    } finally {
      setBusyAction('');
    }
  };

  const toggleAddPaper = (trendId: number) => {
    setMessage('');
    setError('');
    setExpandedTrendIds((current) => current.includes(trendId) ? current : [...current, trendId]);
    setAddingTrendId((current) => (current === trendId ? null : trendId));
  };

  const togglePinnedTrend = (trendId: number) => {
    setExpandedTrendIds((current) => (
      current.includes(trendId) ? current.filter((id) => id !== trendId) : [...current, trendId]
    ));
  };

  const availablePapers = (trend: MonthlyTrend) => {
    const linkedIds = new Set(trend.papers.map((item) => item.paper.id));
    return paperLibrary.filter((paper) => !linkedIds.has(paper.id));
  };

  const filteredPapers = (trend: MonthlyTrend) => {
    const query = (paperQueryByTrend[trend.id] || '').trim().toLowerCase();
    const papers = availablePapers(trend);
    if (!query) return papers;
    return papers.filter((paper) => paper.title.toLowerCase().includes(query));
  };

  const selectPaper = (trendId: number, paper: PaperListItem) => {
    setSelectedPaperByTrend((current) => ({ ...current, [trendId]: String(paper.id) }));
    setPaperQueryByTrend((current) => ({ ...current, [trendId]: paper.title }));
  };

  const addPaper = async (trend: MonthlyTrend) => {
    const paperId = Number(selectedPaperByTrend[trend.id]);
    if (!paperId) {
      setError('请选择要添加的论文');
      return;
    }
    setMessage('');
    setError('');
    setBusyAction(`add-${trend.id}`);
    try {
      setData(await api.addMonthlyTrendPaper(trend.id, paperId));
      setSelectedPaperByTrend((current) => ({ ...current, [trend.id]: '' }));
      setPaperQueryByTrend((current) => ({ ...current, [trend.id]: '' }));
      setAddingTrendId(null);
      setMessage('论文已添加到趋势');
    } catch (err) {
      setError(err instanceof Error ? err.message : '添加论文失败');
    } finally {
      setBusyAction('');
    }
  };

  const removePaper = async (trend: MonthlyTrend, paperId: number) => {
    const lastPaper = trend.papers.length <= 1;
    const prompt = lastPaper
      ? '删除这篇论文后，该趋势卡片也会被删除，确定继续吗？'
      : '确定从该趋势中移除这篇论文吗？';
    if (!window.confirm(prompt)) return;
    setMessage('');
    setError('');
    setBusyAction(`remove-${trend.id}-${paperId}`);
    try {
      await api.removeMonthlyTrendPaper(trend.id, paperId);
      await load(true);
      if (lastPaper) {
        setExpandedTrendIds((current) => current.filter((id) => id !== trend.id));
      }
      setMessage(lastPaper ? '论文已移除，空趋势已删除' : '论文已从趋势中移除');
    } catch (err) {
      setError(err instanceof Error ? err.message : '移除论文失败');
    } finally {
      setBusyAction('');
    }
  };

  const deleteTrend = async (trend: MonthlyTrend) => {
    if (!window.confirm('确定删除这个趋势及其论文关联吗？论文本身不会被删除。')) return;
    setMessage('');
    setError('');
    setBusyAction(`delete-${trend.id}`);
    try {
      await api.deleteMonthlyTrend(trend.id);
      await load(true);
      setExpandedTrendIds((current) => current.filter((id) => id !== trend.id));
      setMessage('趋势已删除');
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除趋势失败');
    } finally {
      setBusyAction('');
    }
  };

  const sortedTrends = data ? [...data.trends].sort((a, b) => b.papers.length - a.papers.length) : [];

  return (
    <section>
      <div className="pageHeader">
        <div>
          <h1>近30天趋势</h1>
          <p>展示 {data?.month || '近30天'} 入库论文归纳出的技术趋势、优质论文和完整入库列表。</p>
        </div>
        <button onClick={() => load(true)} disabled={loading}>{loading ? '刷新中...' : '刷新'}</button>
      </div>
      {error && <div className="error">{error}</div>}
      {message && <div className="success">{message}</div>}
      {loading && <div className="loadingBar"><span className="spinner" />正在加载近30天趋势...</div>}

      <div className="trendSection">
        <h2>技术趋势</h2>
        <div className="trendList">
          {sortedTrends.map((trend) => {
            const isPinned = expandedTrendIds.includes(trend.id);
            return (
            <article className={`trendCard ${isPinned ? 'pinned' : ''}`} key={trend.id}>
              <div className="trendCardHeader">
                <div className="trendCardTitleBlock">
                  <h3>{trend.title}</h3>
                  <span className="trendMetaBadge">{trend.papers.length} 篇论文</span>
                </div>
                <button
                  className="smallButton secondary"
                  type="button"
                  onClick={() => togglePinnedTrend(trend.id)}
                  aria-pressed={isPinned}
                >
                  {isPinned ? '取消固定' : '固定展开'}
                </button>
              </div>
              <div className="trendCardBody">
                {isAdmin && (
                  <div className="trendActions">
                    <button className="smallButton secondary" onClick={() => startEdit(trend)} disabled={!!busyAction}>编辑</button>
                    <button className="smallButton iconButton" onClick={() => toggleAddPaper(trend.id)} disabled={!!busyAction} aria-label="添加论文">＋</button>
                    <button className="smallButton danger" onClick={() => deleteTrend(trend)} disabled={!!busyAction}>
                      {busyAction === `delete-${trend.id}` ? '删除中...' : '删除趋势'}
                    </button>
                  </div>
                )}
                {isAdmin && editingTrendId === trend.id ? (
                  <div className="trendEditForm">
                    <input value={editTitle} onChange={(event) => setEditTitle(event.target.value)} placeholder="趋势标题" />
                    <textarea value={editSummary} onChange={(event) => setEditSummary(event.target.value)} placeholder="趋势总结" />
                    <div className="cardActions">
                      <button className="smallButton" onClick={() => saveTrend(trend.id)} disabled={busyAction === `save-${trend.id}`}>
                        {busyAction === `save-${trend.id}` ? '保存中...' : '保存'}
                      </button>
                      <button className="smallButton secondary" onClick={() => setEditingTrendId(null)} disabled={!!busyAction}>取消</button>
                    </div>
                  </div>
                ) : (
                  <div className="markdownBody compactMarkdown">
                    <ReactMarkdown>{trend.summary}</ReactMarkdown>
                  </div>
                )}
                {isAdmin && addingTrendId === trend.id && (
                  <div className="trendAddPaper">
                    {paperLibraryLoading ? (
                      <div className="meta">正在加载论文库...</div>
                    ) : paperLibraryError ? (
                      <div className="cardError">{paperLibraryError}</div>
                    ) : availablePapers(trend).length ? (
                      <div className="paperPicker">
                        <input
                          value={paperQueryByTrend[trend.id] || ''}
                          onChange={(event) => {
                            setPaperQueryByTrend((current) => ({ ...current, [trend.id]: event.target.value }));
                            setSelectedPaperByTrend((current) => ({ ...current, [trend.id]: '' }));
                          }}
                          placeholder="输入论文标题关键词"
                        />
                        <div className="paperPickerList">
                          {filteredPapers(trend).length ? filteredPapers(trend).map((paper) => (
                            <button
                              className={`paperPickerItem ${selectedPaperByTrend[trend.id] === String(paper.id) ? 'selected' : ''}`}
                              key={paper.id}
                              type="button"
                              onClick={() => selectPaper(trend.id, paper)}
                            >
                              {paper.title}
                            </button>
                          )) : <div className="paperPickerEmpty">没有匹配的论文</div>}
                        </div>
                        <button className="smallButton" onClick={() => addPaper(trend)} disabled={busyAction === `add-${trend.id}`}>
                          {busyAction === `add-${trend.id}` ? '添加中...' : '添加'}
                        </button>
                      </div>
                    ) : (
                      <div className="meta">论文库中没有可添加到该趋势的论文。</div>
                    )}
                  </div>
                )}
                <div className="trendPaperList">
                  {trend.papers.map((item) => (
                    <div className="trendPaperItem" key={item.paper.id}>
                      <div className="trendPaperItemHeader">
                        <Link to={`/papers/${item.paper.id}`}>{item.paper.title}</Link>
                        {isAdmin && (
                          <button
                            className="smallButton danger"
                            onClick={() => removePaper(trend, item.paper.id)}
                            disabled={busyAction === `remove-${trend.id}-${item.paper.id}`}
                          >
                            {busyAction === `remove-${trend.id}-${item.paper.id}` ? '移除中...' : '移除'}
                          </button>
                        )}
                      </div>
                      <p>{item.contribution_summary || item.paper.tech_summary}</p>
                    </div>
                  ))}
                </div>
              </div>
            </article>
            );
          })}
          {data && !data.trends.length && <div className="emptyState">近30天暂未归纳出技术趋势</div>}
        </div>
      </div>

      <div className="trendSection">
        <h2>优质论文</h2>
        <div className="trendList">
          {data?.quality_papers.map((paper) => (
            <article className="trendCard" key={paper.id}>
              <h3><Link to={`/papers/${paper.id}`}>{paper.title}</Link></h3>
              <p>{paper.tech_summary || '该论文被判断为优质论文。'}</p>
              <div className="meta">{paper.authors || '未知作者'}</div>
            </article>
          ))}
          {data && !data.quality_papers.length && <div className="emptyState">近30天暂未发现优质论文</div>}
        </div>
      </div>

      <div className="trendSection">
        <div className="sectionHeaderInline">
          <h2>入库论文列表</h2>
          <div className="segmentedControl">
            <button className={viewMode === 'list' ? 'active' : ''} onClick={() => setViewMode('list')}>列表</button>
            <button className={viewMode === 'cards' ? 'active' : ''} onClick={() => setViewMode('cards')}>卡片</button>
          </div>
        </div>
        {viewMode === 'list' ? (
          <div className="paperListTable">
            {data?.papers.map((paper) => <PaperRow key={paper.id} paper={paper} />)}
            {data && !data.papers.length && <div className="emptyState">近30天暂无入库论文</div>}
          </div>
        ) : (
          <div className="compactPaperGrid">
            {data?.papers.map((paper) => <PaperCard key={paper.id} paper={paper} />)}
            {data && !data.papers.length && <div className="emptyState">近30天暂无入库论文</div>}
          </div>
        )}
      </div>
    </section>
  );
}
