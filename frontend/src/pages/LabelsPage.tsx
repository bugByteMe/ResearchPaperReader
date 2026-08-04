import { useEffect, useState } from 'react';
import { useAuth } from '../auth';
import { api, LabelDefinition } from '../api/client';

export default function LabelsPage() {
  const { isAdmin } = useAuth();
  const [labels, setLabels] = useState<LabelDefinition[]>([]);
  const [type, setType] = useState<LabelDefinition['type']>('category');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');

  const load = async () => setLabels(await api.listLabels());

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  const create = async () => {
    setError('');
    try {
      await api.createLabel({ type, name, description });
      setName('');
      setDescription('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败');
    }
  };

  const remove = async (id: number) => {
    await api.deleteLabel(id);
    await load();
  };

  return (
    <section>
      <h1>标签管理</h1>
      {error && <div className="error">{error}</div>}
      {isAdmin ? (
        <div className="panel formRow">
          <select value={type} onChange={(event) => setType(event.target.value as LabelDefinition['type'])}>
            <option value="category">类别</option>
            <option value="tech_route">技术路线</option>
          </select>
          <input value={name} onChange={(event) => setName(event.target.value)} placeholder="标签名称" />
          <input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="说明" />
          <button onClick={create} disabled={!name.trim()}>新增</button>
        </div>
      ) : <div className="panel">只读模式下可以查看标签，不能新增或删除。</div>}
      <div className="labelList">
        {labels.map((label) => (
          <div className="labelRow" key={label.id}>
            <strong>{label.type === 'category' ? '类别' : '技术路线'}</strong>
            <span>{label.name}</span>
            <span>{label.description}</span>
            {isAdmin && <button onClick={() => remove(label.id)}>删除</button>}
          </div>
        ))}
      </div>
    </section>
  );
}
