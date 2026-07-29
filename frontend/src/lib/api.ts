// API client.
//
// Talks to the FastAPI backend under /api/v1 (same origin in production, where
// FastAPI serves this SPA; overridable via VITE_API_BASE). Attaches a Clerk
// bearer token when available and generates idempotency keys for mutations.

import axios from 'axios';
import type {
  Agent,
  Campaign,
  CampaignCreate,
  PaginatedResponse,
} from '@/types';

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api/v1';

export const http = axios.create({ baseURL: API_BASE });

// The Clerk provider registers a token getter here so the interceptor can attach
// the session token. Left null in demo mode (no Clerk configured).
type TokenGetter = () => Promise<string | null>;
let tokenGetter: TokenGetter | null = null;

export function setAuthTokenGetter(getter: TokenGetter | null): void {
  tokenGetter = getter;
}

http.interceptors.request.use(async (config) => {
  if (tokenGetter) {
    try {
      const token = await tokenGetter();
      if (token) {
        config.headers = config.headers ?? {};
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch {
      // No token available; proceed unauthenticated (demo mode).
    }
  }
  return config;
});

function idempotencyKey(): Record<string, string> {
  const uuid =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return { 'X-Idempotency-Key': uuid };
}

// The backend returns a raw CampaignResponse; normalize it to the frontend
// Campaign shape (which carries share/follow + a flat progress object).
function normalizeCampaign(raw: any): Campaign {
  const actions = raw.actions ?? {};
  const progress = raw.progress ?? {};
  return {
    id: raw.id,
    name: raw.name,
    description: raw.description ?? '',
    status: raw.status,
    target_urls: raw.target_urls ?? [],
    account_ids: raw.account_ids ?? [],
    actions: {
      like: !!actions.like,
      comment: !!actions.comment,
      share: !!actions.share,
      follow: !!actions.follow,
    },
    priority: raw.priority ?? 1,
    progress: {
      total_tasks: progress.total_tasks ?? 0,
      completed_tasks: progress.completed_tasks ?? 0,
      failed_tasks: progress.failed_tasks ?? 0,
    },
    created_at: raw.created_at,
    updated_at: raw.updated_at,
    scheduled_start: raw.scheduled_start_at ?? raw.scheduled_start,
  };
}

export const campaignApi = {
  async list(
    page = 1,
    pageSize = 50,
    status?: string,
  ): Promise<PaginatedResponse<Campaign>> {
    const { data } = await http.get('/campaigns', {
      params: { page, page_size: pageSize, status },
    });
    const items = (data.campaigns ?? []).map(normalizeCampaign);
    const total = data.total ?? items.length;
    const size = data.page_size ?? pageSize;
    return {
      items,
      total,
      page: data.page ?? page,
      page_size: size,
      total_pages: size ? Math.ceil(total / size) : 1,
    };
  },

  async get(id: string): Promise<Campaign> {
    const { data } = await http.get(`/campaigns/${id}`);
    return normalizeCampaign(data);
  },

  async create(payload: CampaignCreate): Promise<Campaign> {
    const { data } = await http.post('/campaigns', payload, {
      headers: idempotencyKey(),
    });
    return normalizeCampaign(data);
  },

  async start(id: string): Promise<void> {
    await http.post(`/campaigns/${id}/start`, null, { headers: idempotencyKey() });
  },

  async pause(id: string): Promise<void> {
    await http.post(`/campaigns/${id}/pause`, null, { headers: idempotencyKey() });
  },
};

export const agentApi = {
  async list(): Promise<Agent[]> {
    const { data } = await http.get('/agents');
    return data as Agent[];
  },
};
