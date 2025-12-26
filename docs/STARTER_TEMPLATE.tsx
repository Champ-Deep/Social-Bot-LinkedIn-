/**
 * STARTER TEMPLATE: Campaign Dashboard with GSAP + Framer Motion
 *
 * This is a complete example showing how GSAP and Framer Motion work together
 * with your existing FastAPI backend.
 *
 * Install dependencies:
 * npm install framer-motion gsap @tanstack/react-query axios
 */

import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import gsap from 'gsap';
import axios from 'axios';

// =============================================================================
// API CLIENT SETUP
// =============================================================================

const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add auth token to all requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// =============================================================================
// TYPE DEFINITIONS
// =============================================================================

interface Campaign {
  id: string;
  name: string;
  description: string;
  status: 'draft' | 'scheduled' | 'running' | 'paused' | 'completed' | 'failed';
  progress: {
    total_tasks: number;
    completed_tasks: number;
    failed_tasks: number;
  };
  created_at: string;
}

interface CampaignTask {
  id: string;
  target_url: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  result?: {
    likes?: number;
    comments?: number;
  };
}

// =============================================================================
// API FUNCTIONS
// =============================================================================

const campaignApi = {
  list: async (page = 1, pageSize = 20): Promise<{ items: Campaign[]; total: number }> => {
    const { data } = await apiClient.get('/campaigns', {
      params: { page, page_size: pageSize }
    });
    return data;
  },

  getById: async (id: string): Promise<Campaign> => {
    const { data } = await apiClient.get(`/campaigns/${id}`);
    return data;
  },

  start: async (id: string) => {
    const { data } = await apiClient.post(`/campaigns/${id}/start`);
    return data;
  },

  pause: async (id: string) => {
    const { data } = await apiClient.post(`/campaigns/${id}/pause`);
    return data;
  },

  getTasks: async (id: string): Promise<{ items: CampaignTask[] }> => {
    const { data } = await apiClient.get(`/campaigns/${id}/tasks`);
    return data;
  }
};

// =============================================================================
// CAMPAIGN CARD COMPONENT (Framer Motion)
// =============================================================================

function CampaignCard({ campaign }: { campaign: Campaign }) {
  const queryClient = useQueryClient();

  const startMutation = useMutation({
    mutationFn: campaignApi.start,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    }
  });

  const pauseMutation = useMutation({
    mutationFn: campaignApi.pause,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    }
  });

  const progress = campaign.progress.total_tasks > 0
    ? (campaign.progress.completed_tasks / campaign.progress.total_tasks) * 100
    : 0;

  const isRunning = campaign.status === 'running';

  const statusColors: Record<Campaign['status'], string> = {
    draft: 'bg-gray-500',
    scheduled: 'bg-purple-500',
    running: 'bg-blue-500',
    paused: 'bg-yellow-500',
    completed: 'bg-green-500',
    failed: 'bg-red-500'
  };

  return (
    <motion.div
      layout // Auto-animate position changes
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.9 }}
      whileHover={{
        scale: 1.02,
        boxShadow: '0 10px 30px rgba(0, 0, 0, 0.15)',
        transition: { duration: 0.2 }
      }}
      whileTap={{ scale: 0.98 }}
      className="bg-white rounded-xl p-6 shadow-md cursor-pointer"
    >
      {/* Status Badge with Pulse */}
      <div className="flex items-center justify-between mb-4">
        <motion.div
          className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-white text-sm font-medium ${statusColors[campaign.status]}`}
          animate={isRunning ? {
            scale: [1, 1.05, 1],
            transition: { duration: 2, repeat: Infinity }
          } : {}}
        >
          {isRunning && (
            <motion.span
              className="w-2 h-2 bg-white rounded-full"
              animate={{
                opacity: [1, 0.3, 1],
                transition: { duration: 1.5, repeat: Infinity }
              }}
            />
          )}
          <span className="capitalize">{campaign.status}</span>
        </motion.div>

        <span className="text-sm text-gray-500">
          {new Date(campaign.created_at).toLocaleDateString()}
        </span>
      </div>

      {/* Campaign Info */}
      <h3 className="text-xl font-bold text-gray-900 mb-2">{campaign.name}</h3>
      <p className="text-gray-600 text-sm mb-4 line-clamp-2">{campaign.description}</p>

      {/* Animated Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between text-sm mb-2">
          <span className="font-medium text-gray-700">Progress</span>
          <motion.span
            key={progress}
            initial={{ scale: 1.2, color: '#3b82f6' }}
            animate={{ scale: 1, color: '#374151' }}
            transition={{ duration: 0.3 }}
            className="font-bold"
          >
            {Math.round(progress)}%
          </motion.span>
        </div>

        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-blue-500 to-blue-600"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 1, ease: 'easeOut' }}
          />
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <StatItem label="Total" value={campaign.progress.total_tasks} delay={0.1} />
        <StatItem label="Done" value={campaign.progress.completed_tasks} delay={0.2} color="text-green-600" />
        <StatItem label="Failed" value={campaign.progress.failed_tasks} delay={0.3} color="text-red-600" />
      </div>

      {/* Action Button */}
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={(e) => {
          e.stopPropagation();
          if (isRunning) {
            pauseMutation.mutate(campaign.id);
          } else if (campaign.status === 'draft' || campaign.status === 'paused') {
            startMutation.mutate(campaign.id);
          }
        }}
        disabled={startMutation.isPending || pauseMutation.isPending}
        className={`w-full py-2 px-4 rounded-lg font-medium text-white ${
          isRunning ? 'bg-yellow-500 hover:bg-yellow-600' : 'bg-green-500 hover:bg-green-600'
        } disabled:opacity-50 disabled:cursor-not-allowed`}
      >
        {startMutation.isPending || pauseMutation.isPending ? (
          <motion.span
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            className="inline-block"
          >
            ⟳
          </motion.span>
        ) : isRunning ? (
          '⏸ Pause'
        ) : (
          '▶ Start'
        )}
      </motion.button>
    </motion.div>
  );
}

function StatItem({
  label,
  value,
  delay = 0,
  color = 'text-gray-900'
}: {
  label: string;
  value: number;
  delay?: number;
  color?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
    >
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <motion.p
        className={`text-2xl font-bold ${color}`}
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 200, delay: delay + 0.1 }}
      >
        {value}
      </motion.p>
    </motion.div>
  );
}

// =============================================================================
// CAMPAIGN LIST COMPONENT (Combined GSAP + Framer Motion)
// =============================================================================

function CampaignList() {
  const containerRef = useRef<HTMLDivElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['campaigns'],
    queryFn: () => campaignApi.list(),
    refetchInterval: 5000 // Poll every 5 seconds for updates
  });

  // GSAP: Animate page entry
  useEffect(() => {
    if (!containerRef.current || !headingRef.current) return;

    const ctx = gsap.context(() => {
      const tl = gsap.timeline();

      // Animate heading
      tl.from(headingRef.current, {
        y: -30,
        opacity: 0,
        duration: 0.6,
        ease: 'power3.out'
      });

      // Stagger animate filter buttons
      tl.from('.filter-button', {
        x: -20,
        opacity: 0,
        stagger: 0.1,
        duration: 0.4
      }, '-=0.3');

    }, containerRef);

    return () => ctx.revert();
  }, []);

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return <ErrorMessage message="Failed to load campaigns" />;
  }

  return (
    <div ref={containerRef} className="max-w-7xl mx-auto px-4 py-8">
      {/* Header with GSAP Animation */}
      <div className="mb-8">
        <h1 ref={headingRef} className="text-4xl font-bold text-gray-900 mb-2">
          LinkedIn Campaigns
        </h1>

        <div className="flex gap-2 mt-4">
          <FilterButton label="All" count={data?.total || 0} active />
          <FilterButton label="Running" count={data?.items.filter(c => c.status === 'running').length || 0} />
          <FilterButton label="Completed" count={data?.items.filter(c => c.status === 'completed').length || 0} />
        </div>
      </div>

      {/* Campaign Grid with Framer Motion */}
      <motion.div
        layout
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
      >
        <AnimatePresence mode="popLayout">
          {data?.items.map((campaign) => (
            <CampaignCard key={campaign.id} campaign={campaign} />
          ))}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}

function FilterButton({
  label,
  count,
  active = false
}: {
  label: string;
  count: number;
  active?: boolean;
}) {
  return (
    <motion.button
      className={`filter-button px-4 py-2 rounded-lg font-medium ${
        active
          ? 'bg-blue-500 text-white'
          : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
      }`}
      whileHover={{ scale: active ? 1 : 1.05 }}
      whileTap={{ scale: 0.95 }}
    >
      {label}
      <span className="ml-2 text-sm opacity-75">({count})</span>
    </motion.button>
  );
}

// =============================================================================
// CAMPAIGN DETAILS PAGE (GSAP Timeline)
// =============================================================================

function CampaignDetails({ id }: { id: string }) {
  const containerRef = useRef<HTMLDivElement>(null);

  const { data: campaign } = useQuery({
    queryKey: ['campaign', id],
    queryFn: () => campaignApi.getById(id)
  });

  const { data: tasksData } = useQuery({
    queryKey: ['campaign-tasks', id],
    queryFn: () => campaignApi.getTasks(id),
    refetchInterval: 3000
  });

  // GSAP: Complex entry animation
  useEffect(() => {
    if (!campaign || !containerRef.current) return;

    const ctx = gsap.context(() => {
      const tl = gsap.timeline();

      tl.from('.detail-header', {
        y: -30,
        opacity: 0,
        duration: 0.5
      })
      .from('.stats-card', {
        y: 20,
        opacity: 0,
        stagger: 0.1,
        duration: 0.4
      }, '-=0.2')
      .from('.task-item', {
        x: -30,
        opacity: 0,
        stagger: 0.05,
        duration: 0.3
      }, '-=0.2');
    }, containerRef);

    return () => ctx.revert();
  }, [campaign, tasksData]);

  if (!campaign) return <LoadingSpinner />;

  return (
    <div ref={containerRef} className="max-w-5xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="detail-header mb-8">
        <h1 className="text-4xl font-bold text-gray-900">{campaign.name}</h1>
        <p className="text-gray-600 mt-2">{campaign.description}</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-3 gap-6 mb-8">
        <div className="stats-card bg-white rounded-lg p-6 shadow-md">
          <h3 className="text-sm text-gray-500 mb-2">Total Tasks</h3>
          <p className="text-3xl font-bold">{campaign.progress.total_tasks}</p>
        </div>

        <div className="stats-card bg-white rounded-lg p-6 shadow-md">
          <h3 className="text-sm text-gray-500 mb-2">Completed</h3>
          <p className="text-3xl font-bold text-green-600">{campaign.progress.completed_tasks}</p>
        </div>

        <div className="stats-card bg-white rounded-lg p-6 shadow-md">
          <h3 className="text-sm text-gray-500 mb-2">Failed</h3>
          <p className="text-3xl font-bold text-red-600">{campaign.progress.failed_tasks}</p>
        </div>
      </div>

      {/* Task List */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-bold mb-4">Tasks</h2>
        <div className="space-y-3">
          {tasksData?.items.map((task) => (
            <div
              key={task.id}
              className="task-item flex items-center justify-between p-4 bg-gray-50 rounded-lg"
            >
              <div className="flex items-center gap-3">
                <TaskStatusIcon status={task.status} />
                <span className="text-sm">{task.target_url}</span>
              </div>

              {task.result && (
                <div className="flex gap-3 text-sm text-gray-600">
                  <span>👍 {task.result.likes || 0}</span>
                  <span>💬 {task.result.comments || 0}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function TaskStatusIcon({ status }: { status: CampaignTask['status'] }) {
  const icons = {
    pending: '⏳',
    in_progress: (
      <motion.span
        animate={{ rotate: 360 }}
        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
      >
        ⟳
      </motion.span>
    ),
    completed: '✅',
    failed: '❌'
  };

  return <span className="text-xl">{icons[status]}</span>;
}

// =============================================================================
// UTILITY COMPONENTS
// =============================================================================

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <motion.div
        className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full"
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
      />
    </div>
  );
}

function ErrorMessage({ message }: { message: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg"
    >
      {message}
    </motion.div>
  );
}

// =============================================================================
// MAIN APP COMPONENT
// =============================================================================

export default function App() {
  const [currentView, setCurrentView] = useState<'list' | 'details'>('list');
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-gray-100">
      <AnimatePresence mode="wait">
        {currentView === 'list' ? (
          <motion.div
            key="list"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <CampaignList />
          </motion.div>
        ) : selectedCampaignId ? (
          <motion.div
            key="details"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <CampaignDetails id={selectedCampaignId} />
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

/**
 * USAGE INSTRUCTIONS:
 *
 * 1. Create a new React project:
 *    npm create vite@latest frontend -- --template react-ts
 *
 * 2. Install dependencies:
 *    npm install framer-motion gsap @tanstack/react-query axios
 *
 * 3. Install Tailwind CSS:
 *    npm install -D tailwindcss postcss autoprefixer
 *    npx tailwindcss init -p
 *
 * 4. Configure Tailwind (tailwind.config.js):
 *    content: ["./index.html", "./src/**\/*.{js,ts,jsx,tsx}"]
 *
 * 5. Add Tailwind directives to index.css:
 *    @tailwind base;
 *    @tailwind components;
 *    @tailwind utilities;
 *
 * 6. Replace App.tsx with this file
 *
 * 7. Wrap with QueryClientProvider in main.tsx:
 *    import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
 *    const queryClient = new QueryClient();
 *    <QueryClientProvider client={queryClient}>
 *      <App />
 *    </QueryClientProvider>
 *
 * 8. Start your FastAPI backend: uvicorn main:app --reload
 *
 * 9. Start your frontend: npm run dev
 */
