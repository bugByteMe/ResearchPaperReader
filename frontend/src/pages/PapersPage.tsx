import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth';
import { api, LabelDefinition, PaperFilters, PaperListItem } from '../api/client';

type PapersPageProps = {
  daily?: boolean;
};

function labelTypeName(type: LabelDefinition['type']) {
  return type === 'category' ? '类别' : '技术路线';
}

function statusText(status: PaperListItem['analysis_status']) {
  if (status === 'queued') return '等待分析';
  if (status === 'running') return '分析中';
  if (status === 'failed') return '分析失败';
  if (status === 'succeeded') return '已分析';
  return '未分析';
}

function formatDate(value: string) {
  return value ? value.slice(0, 10) : '日期未知';
}

export default function PapersPage({ daily = false }: PapersPageProps) {
  const { isAdmin } = useAuth();
  const [papers, setPapers] = useState<PaperListItem[]>([]);
  const [labels, setLabels] = useState<LabelDefinition[]>([]);
  const [selectedLabels, setSelectedLabels] = useState<number[]>([]);
  const [yearFilter, setYearFilter] = useState('');
  const [titleFilter, setTitleFilter] = useState('');
  const [abstractFilter, setAbstractFilter] = useState('');
  const [appliedFilters, setAppliedFilters] = useState<PaperFilters>({});
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [listLoading, setListLoading] = useState(false);
  const [error, setError] = useState('');

  const buildFilters = (): PaperFilters => ({
    year: yearFilter.trim() || undefined,
    title: titleFilter.trim() || undefined,
    abstract: abstractFilter.trim() || undefined,
  });

  const loadPapers = async (labelIds = selectedLabels, filters = appliedFilters, fresh = false) => {
    setError('');
    setListLoading(true);
    const listPapers = daily ? api.listDailyPapers : api.listPapers;
    try {
      const paperData = await listPapers(labelIds, filters, fresh);
      setPapers(paperData);
    } finally {
      setListLoading(false);
    }
  };

  useEffect(() => {
    loadPapers().catch((err) => setError(err.message));
  }, [daily]);

  useEffect(() => {
    api.listLabels().then(setLabels).catch((err) => setError(err.message));
  }, []);

  const search = async () => {
    setLoading(true);
    setError('');
    try {
      setPapers(await api.searchPapers(query || undefined));
    } catch (err) {
      setError(err instanceof Error ? err.message : '搜索失败');
    } finally {
      setLoading(false);
    }
  };

  const refresh = async () => {
    try {
      await loadPapers(selectedLabels, appliedFilters, true);
    } catch (err) {
      setError(err instanceof Error ? err.message : '刷新失败');
    }
  };

  const toggleLabel = async (labelId: number, checked: boolean) => {
    const next = checked ? [...selectedLabels, labelId] : selectedLabels.filter((id) => id !== labelId);
    setSelectedLabels(next);
    try {
      await loadPapers(next, appliedFilters);
    } catch (err) {
      setError(err instanceof Error ? err.message : '筛选失败');
    }
  };

  const applyFilters = async () => {
    const next = buildFilters();
    setAppliedFilters(next);
    try {
      await loadPapers(selectedLabels, next);
    } catch (err) {
      setError(err instanceof Error ? err.message : '检索失败');
    }
  };

  const clearFilters = async () => {
    const emptyFilters: PaperFilters = {};
    setYearFilter('');
    setTitleFilter('');
    setAbstractFilter('');
    setAppliedFilters(emptyFilters);
    try {
      await loadPapers(selectedLabels, emptyFilters);
    } catch (err) {
      setError(err instanceof Error ? err.message : '清空检索失败');
    }
  };

  const remove = async (paperId: number) => {
    if (!window.confirm('确定删除这篇论文吗？')) return;
    await api.deletePaper(paperId);
    await loadPapers();
  };

  const title = daily ? '今日论文' : '论文';
  const description = daily ? '展示今天直接入库且属于目标主题的论文。' : '查看所有已入库且属于目标主题的论文，并按标签检索。';

  return (
    <section>
      <div className="pageHeader">
        <div>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
        <div className="headerActions">
          <button onClick={refresh} disabled={listLoading}>{listLoading ? '刷新中...' : '刷新'}</button>
          {!daily && isAdmin && <button onClick={search} disabled={loading}>{loading ? '搜索中...' : '搜索 arXiv'}</button>}
        </div>
      </div>
      {!daily && (
        <div className="toolbar">
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="留空则使用设置中的关键词" />
        </div>
      )}
      <div className="toolbar">
        <div className="filterTitle">文本检索</div>
        <div className="paperSearchGrid">
          <input value={yearFilter} onChange={(event) => setYearFilter(event.target.value)} placeholder="年份，例如 2025" />
          <input value={titleFilter} onChange={(event) => setTitleFilter(event.target.value)} placeholder="标题关键词" />
          <input value={abstractFilter} onChange={(event) => setAbstractFilter(event.target.value)} placeholder="摘要关键词" />
          <button className="smallButton" onClick={applyFilters} disabled={listLoading}>应用检索</button>
          <button className="smallButton secondary" onClick={clearFilters} disabled={listLoading}>清空</button>
        </div>
      </div>
      <div className="toolbar">
        <div className="filterTitle">依据标签检索</div>
        <div className="filterTags">
          {labels.map((label) => (
            <label key={label.id} className="filterTag">
              <input
                type="checkbox"
                checked={selectedLabels.includes(label.id)}
                onChange={(event) => toggleLabel(label.id, event.target.checked)}
              />
              {labelTypeName(label.type)}：{label.name}
            </label>
          ))}
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      {listLoading && <div className="loadingBar"><span className="spinner" />正在加载论文...</div>}
      <div className="compactPaperGrid">
        {papers.map((paper) => (
          <article className="compactPaperCard" key={paper.id}>
            <div className="cardTopLine">
              <span className="dateText">{formatDate(paper.published_date || paper.created_at)}</span>
              <span className={`statusBadge ${paper.analysis_status}`}>{statusText(paper.analysis_status)}</span>
            </div>
            <h2><Link to={`/papers/${paper.id}`}>{paper.title}</Link></h2>
            <div className="chipRow">
              {paper.labels.length ? paper.labels.map((item) => (
                <span className="chip" key={item.id}>{item.label.name}</span>
              )) : <span className="emptyChip">暂无标签</span>}
            </div>
            <div className="meta">作者：{paper.authors || '未知'}</div>
            <div className="cardActions">
              {!daily && isAdmin ? (
                <button className="smallButton danger" onClick={() => remove(paper.id)}>删除</button>
              ) : null}
            </div>
            {paper.analysis_status === 'failed' && paper.analysis_error && <div className="cardError">{paper.analysis_error}</div>}
          </article>
        ))}
        {!papers.length && !listLoading && <div className="emptyState">暂无论文</div>}
      </div>
    </section>
  );
}
