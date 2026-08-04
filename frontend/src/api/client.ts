export type PaperListItem = {
  id: number;
  title: string;
  published_date: string;
  authors: string;
  last_analyzed_at: string | null;
  analysis_status: 'pending' | 'queued' | 'running' | 'succeeded' | 'failed';
  analysis_error: string;
  workflow_status: 'accepted';
  has_new_trend: boolean;
  is_quality: boolean;
  created_at: string;
  labels: Array<{ id: number; source: string; label: LabelDefinition }>;
};

export type PaperFilters = {
  year?: string;
  title?: string;
  abstract?: string;
};

export type LabelDefinition = {
  id: number;
  type: 'category' | 'tech_route';
  name: string;
  description: string;
};

export type Paper = PaperListItem & {
  arxiv_id: string;
  url: string;
  pdf_url: string;
  abstract: string;
  updated_date: string;
  agent_answer: string;
  category_answer: string;
  tech_route_answer: string;
  tech_summary: string;
  relevance_answer: string;
  trend_answer: string;
  quality_answer: string;
  is_relevant: boolean;
  labels: Array<{ id: number; source: string; label: LabelDefinition }>;
};

export type PromptType = 'relevance' | 'category' | 'tech_route' | 'trend' | 'quality' | 'tech_summary' | 'trend_merge' | 'knowledge_update';

export type Prompt = {
  id: number;
  type: PromptType;
  content: string;
  is_active: boolean;
  updated_at: string;
};

export type MonthlyTrend = {
  id: number;
  month: string;
  title: string;
  summary: string;
  papers: Array<{ paper: Pick<PaperListItem, 'id' | 'title'> & { tech_summary: string }; contribution_summary: string }>;
};

export type MonthlyTrends = {
  month: string;
  trends: MonthlyTrend[];
  quality_papers: Array<PaperListItem & { tech_summary: string }>;
  papers: PaperListItem[];
};

export type Setting = {
  key: string;
  value: string;
};

export type Workspace = {
  id: number;
  name: string;
  description: string;
  analysis_language: string;
  arxiv_query: string;
  arxiv_categories: string;
  arxiv_daily_lookback_days: number;
  arxiv_max_results: number;
  arxiv_sort_by: 'submitted_date' | 'last_updated_date' | 'relevance';
  arxiv_sort_order: 'ascending' | 'descending';
  knowledge_base_auto_update_enabled: boolean;
  is_configured: boolean;
};

export type WorkspaceSetup = Omit<Workspace, 'id' | 'is_configured'> & {
  knowledge_base: string;
  labels: Array<{ type: 'category' | 'tech_route'; name: string; description: string }>;
};

export type KnowledgeBase = {
  id: number;
  content: string;
  updated_at: string;
};

export type DailyRefreshRun = {
  id: number;
  status: 'running' | 'succeeded' | 'failed';
  trigger_type: 'scheduled' | 'manual';
  matched: number;
  imported: number;
  skipped_existing: number;
  analyzed: number;
  date_from: string;
  date_to: string;
  query: string;
  categories: string;
  sort_by: string;
  sort_order: string;
  error_message: string;
  started_at: string;
  finished_at: string | null;
};

export type UserRole = 'admin' | 'reader';

export type CurrentUser = {
  role: UserRole;
};

type CacheEntry = {
  expiresAt: number;
  value?: unknown;
  promise?: Promise<unknown>;
};

const getCache = new Map<string, CacheEntry>();

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    credentials: 'include',
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail === 'Admin privileges required' ? '只读用户无权执行此操作' : error.detail || 'Request failed');
  }
  return response.json() as Promise<T>;
}

async function cachedGet<T>(path: string, ttlMs: number): Promise<T> {
  const now = Date.now();
  const cached = getCache.get(path);
  if (cached?.value !== undefined && cached.expiresAt > now) {
    return cached.value as T;
  }
  if (cached?.promise) {
    return cached.promise as Promise<T>;
  }

  const promise = request<T>(path)
    .then((value) => {
      getCache.set(path, { value, expiresAt: Date.now() + ttlMs });
      return value;
    })
    .catch((error) => {
      getCache.delete(path);
      throw error;
    });
  getCache.set(path, { value: cached?.value, expiresAt: cached?.expiresAt || 0, promise });
  return promise;
}

async function freshGet<T>(path: string, ttlMs: number): Promise<T> {
  getCache.delete(path);
  return cachedGet<T>(path, ttlMs);
}

function clearCache(prefix: string) {
  for (const key of getCache.keys()) {
    if (key.startsWith(prefix)) getCache.delete(key);
  }
}

function paperListQuery(labelIds: number[], filters: PaperFilters = {}) {
  const params = new URLSearchParams();
  labelIds.forEach((id) => params.append('label_ids', String(id)));
  if (filters.year) params.set('year', filters.year);
  if (filters.title) params.set('title', filters.title);
  if (filters.abstract) params.set('abstract', filters.abstract);
  const query = params.toString();
  return query ? `?${query}` : '';
}

export const api = {
  getCurrentUser: () => request<CurrentUser>('/api/auth/me'),
  getWorkspace: () => freshGet<Workspace | null>('/api/workspace', 3000),
  setupWorkspace: (payload: WorkspaceSetup) => request<Workspace>('/api/workspace/setup', { method: 'POST', body: JSON.stringify(payload) }).then((value) => {
    clearCache('/api/workspace');
    return value;
  }),
  updateWorkspace: (payload: Omit<Workspace, 'id' | 'is_configured'>) => request<Workspace>('/api/workspace', { method: 'PUT', body: JSON.stringify(payload) }).then((value) => {
    clearCache('/api/workspace');
    return value;
  }),
  login: (password: string) => request<CurrentUser>('/api/auth/login', { method: 'POST', body: JSON.stringify({ password }) }),
  logout: () => request<CurrentUser>('/api/auth/logout', { method: 'POST' }),
  listPapers: (labelIds: number[] = [], filters: PaperFilters = {}, fresh = false) => {
    const path = `/api/papers${paperListQuery(labelIds, filters)}`;
    return fresh ? freshGet<PaperListItem[]>(path, 3000) : cachedGet<PaperListItem[]>(path, 3000);
  },
  listDailyPapers: (labelIds: number[] = [], filters: PaperFilters = {}, fresh = false) => {
    const path = `/api/papers/daily${paperListQuery(labelIds, filters)}`;
    return fresh ? freshGet<PaperListItem[]>(path, 3000) : cachedGet<PaperListItem[]>(path, 3000);
  },
  listMonthlyTrends: (fresh = false) => {
    const path = '/api/papers/monthly-trends';
    return fresh ? freshGet<MonthlyTrends>(path, 3000) : cachedGet<MonthlyTrends>(path, 3000);
  },
  updateMonthlyTrend: (trendId: number, payload: Pick<MonthlyTrend, 'title' | 'summary'>) =>
    request<MonthlyTrends>(`/api/papers/monthly-trends/${trendId}`, { method: 'PATCH', body: JSON.stringify(payload) }).then((value) => {
      clearCache('/api/papers');
      return value;
    }),
  addMonthlyTrendPaper: (trendId: number, paperId: number) =>
    request<MonthlyTrends>(`/api/papers/monthly-trends/${trendId}/papers`, { method: 'POST', body: JSON.stringify({ paper_id: paperId }) }).then((value) => {
      clearCache('/api/papers');
      return value;
    }),
  removeMonthlyTrendPaper: (trendId: number, paperId: number) =>
    request<{ deleted_trend: boolean }>(`/api/papers/monthly-trends/${trendId}/papers/${paperId}`, { method: 'DELETE' }).then((value) => {
      clearCache('/api/papers');
      return value;
    }),
  deleteMonthlyTrend: (trendId: number) =>
    request<{ message: string }>(`/api/papers/monthly-trends/${trendId}`, { method: 'DELETE' }).then((value) => {
      clearCache('/api/papers');
      return value;
    }),
  getPaper: (id: number) => request<Paper>(`/api/papers/${id}`),
  searchPapers: (query?: string, maxResults?: number) =>
    request<PaperListItem[]>('/api/papers/search', {
      method: 'POST',
      body: JSON.stringify({ query, max_results: maxResults }),
    }).then((value) => {
      clearCache('/api/papers');
      return value;
    }),
  refreshPaper: (id: number) => request<{ job_id: number; status: string }>(`/api/papers/${id}/refresh`, { method: 'POST' }).then((value) => {
    clearCache('/api/papers');
    return value;
  }),
  updatePaperLabels: (id: number, labelIds: number[]) =>
    request<Paper>(`/api/papers/${id}/labels`, { method: 'PATCH', body: JSON.stringify({ label_ids: labelIds }) }).then((value) => {
      clearCache('/api/papers');
      return value;
    }),
  deletePaper: (id: number) => request<{ message: string }>(`/api/papers/${id}`, { method: 'DELETE' }).then((value) => {
    clearCache('/api/papers');
    return value;
  }),
  listPrompts: () => cachedGet<Prompt[]>('/api/prompts', 30000),
  updatePrompt: (type: Prompt['type'], content: string) =>
    request<Prompt>(`/api/prompts/${type}`, { method: 'PUT', body: JSON.stringify({ content }) }).then((value) => {
      clearCache('/api/prompts');
      return value;
    }),
  listLabels: (type?: LabelDefinition['type']) => cachedGet<LabelDefinition[]>(`/api/labels${type ? `?type=${type}` : ''}`, 60000),
  createLabel: (payload: Omit<LabelDefinition, 'id'>) =>
    request<LabelDefinition>('/api/labels', { method: 'POST', body: JSON.stringify(payload) }).then((value) => {
      clearCache('/api/labels');
      return value;
    }),
  updateLabel: (id: number, payload: Partial<Pick<LabelDefinition, 'name' | 'description'>>) =>
    request<LabelDefinition>(`/api/labels/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }).then((value) => {
      clearCache('/api/labels');
      return value;
    }),
  deleteLabel: (id: number) => request<{ message: string }>(`/api/labels/${id}`, { method: 'DELETE' }).then((value) => {
    clearCache('/api/labels');
    return value;
  }),
  listSettings: () => cachedGet<Setting[]>('/api/settings', 30000),
  updateSetting: (key: string, value: string) =>
    request<Setting>(`/api/settings/${key}`, { method: 'PUT', body: JSON.stringify({ value }) }).then((setting) => {
      clearCache('/api/settings');
      return setting;
    }),
  runScheduledRefresh: () => request<{ imported: number; analyzed: number; message: string }>('/api/jobs/run-scheduled-refresh', { method: 'POST' }).then((value) => {
    clearCache('/api/papers');
    clearCache('/api/jobs/daily-refresh-runs');
    return value;
  }),
  getKnowledgeBase: () => cachedGet<KnowledgeBase>('/api/knowledge-base', 3000),
  updateKnowledgeBase: (content: string) =>
    request<KnowledgeBase>('/api/knowledge-base', { method: 'PUT', body: JSON.stringify({ content }) }).then((value) => {
      clearCache('/api/knowledge-base');
      return value;
    }),
  listDailyRefreshRuns: (fresh = false) => {
    const path = '/api/jobs/daily-refresh-runs';
    return fresh ? freshGet<DailyRefreshRun[]>(path, 3000) : cachedGet<DailyRefreshRun[]>(path, 3000);
  },
};
