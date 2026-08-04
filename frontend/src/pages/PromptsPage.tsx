import { useEffect, useState } from 'react';
import { useAuth } from '../auth';
import { api, Prompt } from '../api/client';

const promptTitle: Record<Prompt['type'], string> = {
  relevance: '主题筛选 Prompt',
  category: '类别 Prompt',
  tech_route: '技术路线 Prompt',
  trend: '新技术趋势 Prompt',
  quality: '优质论文 Prompt',
  tech_summary: '技术方案摘要 Prompt',
  trend_merge: '趋势归纳合并 Prompt',
  knowledge_update: '知识库更新 Prompt',
};

export default function PromptsPage() {
  const { isAdmin } = useAuth();
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [savingType, setSavingType] = useState<Prompt['type'] | ''>('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    api.listPrompts().then(setPrompts).catch((err) => setError(err.message));
  }, []);

  const save = async (prompt: Prompt) => {
    setMessage('');
    setError('');
    setSavingType(prompt.type);
    try {
      const updated = await api.updatePrompt(prompt.type, prompt.content);
      setPrompts((current) => current.map((item) => item.type === updated.type ? updated : item));
      setMessage(`${promptTitle[updated.type]} 已保存`);
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSavingType('');
    }
  };

  return (
    <section>
      <h1>Prompt 管理</h1>
      <p>{isAdmin ? '这些 Prompt 会用于后续 AI 分析任务。' : '只读模式下可以查看 Prompt，不能修改。'}</p>
      {error && <div className="error">{error}</div>}
      {message && <div className="success">{message}</div>}
      {prompts.map((prompt) => (
        <div className="panel" key={prompt.type}>
          <h2>{promptTitle[prompt.type]}</h2>
          <textarea readOnly={!isAdmin} value={prompt.content} onChange={(event) => setPrompts((current) => current.map((item) => item.id === prompt.id ? { ...item, content: event.target.value } : item))} />
          {isAdmin && <button onClick={() => save(prompt)} disabled={savingType === prompt.type}>{savingType === prompt.type ? '保存中...' : '保存'}</button>}
        </div>
      ))}
    </section>
  );
}
