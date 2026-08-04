import { useEffect, useState } from 'react';
import rehypeKatex from 'rehype-katex';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import { useParams } from 'react-router-dom';
import { useAuth } from '../auth';
import { api, LabelDefinition, Paper } from '../api/client';
import 'katex/dist/katex.min.css';


function isAnalyzing(status: Paper['analysis_status']) {
  return status === 'queued' || status === 'running';
}

function statusText(status: Paper['analysis_status']) {
  if (status === 'queued') return '等待分析';
  if (status === 'running') return '分析中';
  if (status === 'failed') return '分析失败';
  if (status === 'succeeded') return '已分析';
  return '未分析';
}

export default function PaperDetailPage() {
  const { isAdmin } = useAuth();
  const { id } = useParams();
  const paperId = Number(id);
  const [paper, setPaper] = useState<Paper | null>(null);
  const [labels, setLabels] = useState<LabelDefinition[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    const [paperData, labelData] = await Promise.all([api.getPaper(paperId), api.listLabels()]);
    setPaper(paperData);
    setLabels(labelData);
    setSelected(paperData.labels.map((item) => item.label.id));
  };

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, [paperId]);

  useEffect(() => {
    if (!paper || !isAnalyzing(paper.analysis_status)) return;
    const timer = window.setInterval(() => {
      api.getPaper(paperId).then(setPaper).catch((err) => setError(err.message));
    }, 4000);
    return () => window.clearInterval(timer);
  }, [paper, paperId]);

  const refresh = async () => {
    setBusy(true);
    setError('');
    try {
      await api.refreshPaper(paperId);
      setPaper(await api.getPaper(paperId));
    } catch (err) {
      setError(err instanceof Error ? err.message : '刷新失败');
    } finally {
      setBusy(false);
    }
  };

  const saveLabels = async () => {
    setBusy(true);
    try {
      const updated = await api.updatePaperLabels(paperId, selected);
      setPaper(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存标签失败');
    } finally {
      setBusy(false);
    }
  };

  if (!paper) return <div>{error || '加载中...'}</div>;

  return (
    <section>
      <div className="pageHeader">
        <div>
          <h1>{paper.title}</h1>
          <p>{paper.authors}</p>
        </div>
        {isAdmin && <button onClick={refresh} disabled={busy}>{busy ? '处理中...' : '刷新 AI 分析'}</button>}
      </div>
      {error && <div className="error">{error}</div>}
      <div className="detailLinks">
        <a href={paper.url} target="_blank" rel="noreferrer">arXiv</a>
        <a href={paper.pdf_url} target="_blank" rel="noreferrer">PDF</a>
        <span>最近分析：{paper.last_analyzed_at || '从未分析'}</span>
        <span className={`statusBadge ${paper.analysis_status}`}>{statusText(paper.analysis_status)}</span>
        <span className="chip">{paper.is_relevant ? '目标主题' : '非目标主题'}</span>
        <span className="chip">{paper.has_new_trend ? '有新技术趋势' : '无新技术趋势'}</span>
        <span className="chip">{paper.is_quality ? '优质论文' : '普通论文'}</span>
      </div>
      {paper.analysis_status === 'failed' && paper.analysis_error && <div className="error">{paper.analysis_error}</div>}
      <div className="panel">
        <h2>摘要</h2>
        <p>{paper.abstract}</p>
      </div>
      {paper.tech_summary && (
        <div className="panel">
          <h2>技术方案摘要</h2>
          <p>{paper.tech_summary}</p>
        </div>
      )}
      <div className="panel">
        <h2>人工标签</h2>
        {isAdmin ? (
          <>
            <div className="labelPicker">
              {labels.map((label) => (
                <label key={label.id}>
                  <input
                    type="checkbox"
                    checked={selected.includes(label.id)}
                    onChange={(event) => {
                      setSelected((current) => event.target.checked ? [...current, label.id] : current.filter((item) => item !== label.id));
                    }}
                  />
                  {label.type === 'category' ? '类别' : '技术路线'}：{label.name}
                </label>
              ))}
            </div>
            <button onClick={saveLabels} disabled={busy}>保存标签</button>
          </>
        ) : (
          <div className="chipRow">
            {paper.labels.length ? paper.labels.map((item) => <span className="chip" key={item.id}>{item.label.name}</span>) : <span className="emptyChip">暂无标签</span>}
          </div>
        )}
      </div>
      <div className="panel">
        <h2>Agent Answer</h2>
        {paper.agent_answer ? (
          <div className="markdownBody">
            <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
              {paper.agent_answer}
            </ReactMarkdown>
          </div>
        ) : <p>暂无分析结果。</p>}
      </div>
    </section>
  );
}
