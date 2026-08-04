import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useAuth } from '../auth';
import { api, KnowledgeBase } from '../api/client';

export default function KnowledgeBasePage() {
  const { isAdmin } = useAuth();
  const [knowledgeBase, setKnowledgeBase] = useState<KnowledgeBase | null>(null);
  const [content, setContent] = useState('');
  const [autoUpdateEnabled, setAutoUpdateEnabled] = useState(true);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [toggleSaving, setToggleSaving] = useState(false);

  useEffect(() => {
    Promise.all([api.getKnowledgeBase(), api.listSettings()])
      .then(([knowledge, settings]) => {
        setKnowledgeBase(knowledge);
        setContent(knowledge.content);
        const setting = settings.find((item) => item.key === 'knowledge_base_auto_update_enabled');
        setAutoUpdateEnabled((setting?.value || 'true').toLowerCase() !== 'false');
      })
      .catch((err) => setError(err.message));
  }, []);

  const save = async () => {
    setMessage('');
    setError('');
    setSaving(true);
    try {
      const updated = await api.updateKnowledgeBase(content);
      setKnowledgeBase(updated);
      setContent(updated.content);
      setMessage('知识库已保存');
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const toggleAutoUpdate = async () => {
    const nextValue = !autoUpdateEnabled;
    setMessage('');
    setError('');
    setToggleSaving(true);
    try {
      await api.updateSetting('knowledge_base_auto_update_enabled', nextValue ? 'true' : 'false');
      setAutoUpdateEnabled(nextValue);
      setMessage(nextValue ? '已恢复 AI 自动更新知识库' : '已暂停 AI 自动更新知识库');
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存开关失败');
    } finally {
      setToggleSaving(false);
    }
  };

  return (
    <section>
      <div className="pageHeader">
        <div>
          <h1>领域知识库</h1>
          <p>{isAdmin ? 'AI 会在分析新论文时参考这里的内容，并在分析完成后自动沉淀新的领域总结。你也可以手动修改。' : '只读模式下可以查看知识库，不能修改内容或自动更新设置。'}</p>
          {knowledgeBase && <div className="meta">最后更新：{new Date(knowledgeBase.updated_at).toLocaleString()}</div>}
        </div>
        {isAdmin && <button onClick={save} disabled={saving}>{saving ? '保存中...' : '保存知识库'}</button>}
      </div>
      {error && <div className="error">{error}</div>}
      {message && <div className="success">{message}</div>}
      {isAdmin && <div className="panel switchPanel">
        <div>
          <h2>AI 自动更新</h2>
          <p>{autoUpdateEnabled ? '开启后，AI 每分析完一篇论文都会尝试沉淀知识库。' : '暂停后，AI 分析论文时仍会参考知识库，但不会自动改写知识库。'}</p>
        </div>
        <button className={autoUpdateEnabled ? '' : 'secondaryButton'} onClick={toggleAutoUpdate} disabled={toggleSaving}>
          {toggleSaving ? '保存中...' : autoUpdateEnabled ? '暂停自动更新' : '恢复自动更新'}
        </button>
      </div>}
      <div className="knowledgeGrid">
        <div className="panel knowledgeEditorPanel">
          <h2>编辑</h2>
          <textarea className="knowledgeTextarea" readOnly={!isAdmin} value={content} onChange={(event) => setContent(event.target.value)} />
        </div>
        <div className="panel knowledgePreviewPanel">
          <h2>预览</h2>
          <div className="markdownBody">
            <ReactMarkdown>{content || '暂无内容'}</ReactMarkdown>
          </div>
        </div>
      </div>
    </section>
  );
}
