// Campaign Types
export type CampaignStatus =
  | 'draft'
  | 'scheduled'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type TaskStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'skipped'
  | 'rate_limited';

export type AgentStatus =
  | 'idle'
  | 'processing'
  | 'waiting'
  | 'error';

export interface CampaignProgress {
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
}

export interface Campaign {
  id: string;
  name: string;
  description: string;
  status: CampaignStatus;
  target_urls: string[];
  account_ids: string[];
  actions: {
    like: boolean;
    comment: boolean;
    share: boolean;
    follow: boolean;
  };
  priority: number;
  progress: CampaignProgress;
  created_at: string;
  updated_at: string;
  scheduled_start?: string;
}

export interface CampaignTask {
  id: string;
  campaign_id: string;
  orchestrator_task_id?: string;
  target_url: string;
  status: TaskStatus;
  result?: {
    likes?: number;
    comments?: number;
    shares?: number;
    error?: string;
  };
  created_at: string;
  updated_at: string;
}

export interface CampaignCreate {
  name: string;
  description: string;
  target_urls: string[];
  account_ids: string[];
  actions: {
    like: boolean;
    comment: boolean;
    share: boolean;
    follow: boolean;
  };
  priority?: number;
  scheduled_start?: string;
}

export interface CampaignUpdate {
  name?: string;
  description?: string;
  status?: CampaignStatus;
  target_urls?: string[];
  account_ids?: string[];
  actions?: {
    like?: boolean;
    comment?: boolean;
    share?: boolean;
    follow?: boolean;
  };
  priority?: number;
  scheduled_start?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Agent Types
export interface Agent {
  id: string;
  name: string;
  type: 'account_manager' | 'content_analysis' | 'interaction' | 'conversation' | 'safety';
  status: AgentStatus;
  current_task?: string;
  tasks_completed: number;
  tasks_failed: number;
  last_activity: string;
}

export interface AgentMessage {
  id: string;
  agent_id: string;
  type: 'COMMAND' | 'QUERY' | 'RESPONSE' | 'EVENT' | 'ERROR' | 'HEALTH_CHECK' | 'STATE_UPDATE';
  priority: 'LOW' | 'NORMAL' | 'HIGH' | 'CRITICAL';
  content: any;
  timestamp: string;
}

// WebSocket Message Types
export interface WSMessage {
  type: 'CAMPAIGN_UPDATE' | 'TASK_COMPLETED' | 'TASK_FAILED' | 'AGENT_STATUS' | 'PROGRESS_UPDATE';
  campaign_id?: string;
  task_id?: string;
  agent_id?: string;
  data: any;
  timestamp: string;
}

// Auth Types
export interface User {
  id: string;
  email: string;
  name?: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}
