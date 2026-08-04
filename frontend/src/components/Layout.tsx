import { FormEvent, useEffect, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../auth';
import { api, Workspace } from '../api/client';

export default function Layout() {
  const { isAdmin, loading, login, logout } = useAuth();
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  useEffect(() => { api.getWorkspace().then(setWorkspace).catch(() => setWorkspace(null)); }, []);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    try {
      await login(password);
      setPassword('');
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败');
    }
  };

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">AutoPaperReader</div>
        {workspace && <div className="meta">{workspace.name}</div>}
        <div className="authBox">
          <div className="meta">当前模式：{loading ? '加载中...' : isAdmin ? '管理员' : '只读'}</div>
          {isAdmin ? (
            <button className="smallButton secondary" onClick={() => logout().catch((err) => setError(err instanceof Error ? err.message : '退出失败'))}>退出管理员</button>
          ) : (
            <form onSubmit={submit}>
              <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="管理员密码" />
              <button className="smallButton" disabled={!password.trim()}>登录</button>
            </form>
          )}
          {error && <div className="cardError">{error}</div>}
        </div>
        <nav>
          {!workspace && <NavLink to="/setup">初始化</NavLink>}
          <NavLink to="/papers">论文</NavLink>
          <NavLink to="/monthly">近30天趋势</NavLink>
          <NavLink to="/knowledge-base">知识库</NavLink>
          <NavLink to="/logs">日志</NavLink>
          <NavLink to="/prompts">Prompt</NavLink>
          <NavLink to="/labels">标签</NavLink>
          <NavLink to="/settings">设置</NavLink>
        </nav>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
