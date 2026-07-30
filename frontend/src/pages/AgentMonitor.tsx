import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import gsap from 'gsap';
import {
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  Zap,
  Shield,
  MessageSquare,
  Eye,
  UserCheck,
} from 'lucide-react';
import { agentApi } from '@/lib/api';
import { useGeneralWebSocket } from '@/hooks/useWebSocket';
import type { Agent, AgentStatus } from '@/types';
import { clsx } from 'clsx';
import { formatDistanceToNow } from 'date-fns';

const agentIcons = {
  account_manager: UserCheck,
  content_analysis: Eye,
  interaction: Zap,
  conversation: MessageSquare,
  safety: Shield,
};

const agentColors = {
  account_manager: 'from-blue-500 to-blue-600',
  content_analysis: 'from-purple-500 to-purple-600',
  interaction: 'from-green-500 to-green-600',
  conversation: 'from-orange-500 to-orange-600',
  safety: 'from-red-500 to-red-600',
};

export function AgentMonitor() {
  const containerRef = useRef<HTMLDivElement>(null);

  // Connect to WebSocket for real-time updates
  const { isConnected, lastMessage } = useGeneralWebSocket();

  // Fetch agents
  const { data: agents, isLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: agentApi.list,
    refetchInterval: 3000, // Refetch every 3 seconds
  });

  // GSAP: Animate page entry
  useEffect(() => {
    if (!containerRef.current || !agents) return;

    const ctx = gsap.context(() => {
      const tl = gsap.timeline();

      // Animate header
      tl.from('.monitor-header', {
        y: -30,
        opacity: 0,
        duration: 0.6,
        ease: 'power3.out',
      });

      // Stagger animate agent cards
      tl.from(
        '.agent-card',
        {
          y: 50,
          opacity: 0,
          stagger: 0.1,
          duration: 0.5,
          ease: 'power2.out',
        },
        '-=0.3'
      );

      // Animate stats cards
      tl.from(
        '.stat-card',
        {
          scale: 0.8,
          opacity: 0,
          stagger: 0.1,
          duration: 0.4,
        },
        '-=0.3'
      );
    }, containerRef);

    return () => ctx.revert();
  }, [agents]);

  // Pulse animation for processing agents
  useEffect(() => {
    if (!containerRef.current) return;

    const ctx = gsap.context(() => {
      gsap.to('.agent-card.processing', {
        boxShadow: '0 0 25px rgba(59, 130, 246, 0.4)',
        duration: 1.5,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
      });
    }, containerRef);

    return () => ctx.revert();
  }, [agents]);

  // Calculate stats
  const stats = agents
    ? {
        total: agents.length,
        active: agents.filter((a) => a.status === 'processing').length,
        idle: agents.filter((a) => a.status === 'idle').length,
        totalCompleted: agents.reduce((sum, a) => sum + a.tasks_completed, 0),
        totalFailed: agents.reduce((sum, a) => sum + a.tasks_failed, 0),
      }
    : null;

  if (isLoading) {
    return <LoadingState />;
  }

  return (
    <div ref={containerRef} className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4">
        {/* Header */}
        <div className="monitor-header mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold text-gray-900 mb-2">
                Agent Activity Monitor
              </h1>
              <p className="text-gray-600">
                Real-time status of all automation agents
                {isConnected && (
                  <span className="ml-2 inline-flex items-center gap-1 text-sm text-green-600">
                    <motion.span
                      className="w-2 h-2 bg-green-500 rounded-full"
                      animate={{
                        opacity: [1, 0.3, 1],
                        transition: { duration: 2, repeat: Infinity },
                      }}
                    />
                    Live
                  </span>
                )}
              </p>
            </div>

            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 10, repeat: Infinity, ease: 'linear' }}
              className="text-linkedin-500"
            >
              <Activity size={48} />
            </motion.div>
          </div>

          {/* Stats Cards */}
          {stats && (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <StatsCard
                label="Total Agents"
                value={stats.total}
                icon={<Activity size={20} />}
                color="text-gray-700"
              />
              <StatsCard
                label="Active"
                value={stats.active}
                icon={<Zap size={20} />}
                color="text-blue-600"
              />
              <StatsCard
                label="Idle"
                value={stats.idle}
                icon={<Clock size={20} />}
                color="text-gray-600"
              />
              <StatsCard
                label="Completed"
                value={stats.totalCompleted}
                icon={<CheckCircle2 size={20} />}
                color="text-green-600"
              />
              <StatsCard
                label="Failed"
                value={stats.totalFailed}
                icon={<XCircle size={20} />}
                color="text-red-600"
              />
            </div>
          )}
        </div>

        {/* Agent Cards */}
        <div className="space-y-4">
          {agents?.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>

        {/* Message Flow Visualization */}
        {lastMessage && (
          <MessageNotification message={lastMessage.type} />
        )}
      </div>
    </div>
  );
}

interface StatsCardProps {
  label: string;
  value: number;
  icon: React.ReactNode;
  color: string;
}

function StatsCard({ label, value, icon, color }: StatsCardProps) {
  return (
    <motion.div
      className="stat-card bg-white rounded-lg p-4 shadow-md"
      whileHover={{ scale: 1.05, y: -5 }}
      transition={{ type: 'spring', stiffness: 300 }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-600">{label}</span>
        <span className={color}>{icon}</span>
      </div>
      <motion.p
        className={clsx('text-3xl font-bold', color)}
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 200, delay: 0.1 }}
      >
        {value}
      </motion.p>
    </motion.div>
  );
}

interface AgentCardProps {
  agent: Agent;
}

function AgentCard({ agent }: AgentCardProps) {
  const Icon = agentIcons[agent.type];
  const gradientColor = agentColors[agent.type];

  return (
    <motion.div
      layout
      className={clsx(
        'agent-card bg-white rounded-xl p-6 shadow-md border-2',
        agent.status === 'processing' ? 'processing border-blue-200' : 'border-gray-200'
      )}
      whileHover={{ scale: 1.01 }}
      transition={{ type: 'spring', stiffness: 300 }}
    >
      <div className="flex items-start gap-6">
        {/* Agent Icon */}
        <motion.div
          className={clsx(
            'w-16 h-16 rounded-xl bg-gradient-to-br',
            gradientColor,
            'flex items-center justify-center text-white shadow-lg'
          )}
          animate={
            agent.status === 'processing'
              ? {
                  rotate: [0, 5, -5, 0],
                  transition: { duration: 2, repeat: Infinity },
                }
              : {}
          }
        >
          <Icon size={32} />
        </motion.div>

        {/* Agent Info */}
        <div className="flex-1">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xl font-bold text-gray-900">{agent.name}</h3>
            <StatusBadge status={agent.status} />
          </div>

          {agent.current_task && (
            <div className="mb-4">
              <p className="text-sm text-gray-600">Current Task:</p>
              <p className="text-sm font-medium text-gray-900">
                {agent.current_task}
              </p>
            </div>
          )}

          {/* Progress Bar (if processing) */}
          {agent.status === 'processing' && (
            <div className="mb-4">
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-blue-500 to-blue-600"
                  initial={{ width: '0%' }}
                  animate={{ width: '100%' }}
                  transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
                />
              </div>
            </div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-xs text-gray-500">Completed</p>
              <p className="text-lg font-bold text-green-600">
                {agent.tasks_completed}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Failed</p>
              <p className="text-lg font-bold text-red-600">
                {agent.tasks_failed}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Last Active</p>
              <p className="text-lg font-bold text-gray-700">
                {formatDistanceToNow(new Date(agent.last_activity), {
                  addSuffix: true,
                })}
              </p>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function StatusBadge({ status }: { status: AgentStatus }) {
  const config = {
    idle: {
      bg: 'bg-gray-100',
      text: 'text-gray-700',
      dot: 'bg-gray-500',
    },
    processing: {
      bg: 'bg-blue-100',
      text: 'text-blue-700',
      dot: 'bg-blue-500',
    },
    waiting: {
      bg: 'bg-yellow-100',
      text: 'text-yellow-700',
      dot: 'bg-yellow-500',
    },
    error: {
      bg: 'bg-red-100',
      text: 'text-red-700',
      dot: 'bg-red-500',
    },
  };

  const { bg, text, dot } = config[status];

  return (
    <motion.div
      className={clsx(
        'inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium',
        bg,
        text
      )}
      animate={
        status === 'processing'
          ? {
              scale: [1, 1.05, 1],
              transition: { duration: 2, repeat: Infinity },
            }
          : {}
      }
    >
      <motion.span
        className={clsx('w-2 h-2 rounded-full', dot)}
        animate={
          status === 'processing'
            ? {
                opacity: [1, 0.3, 1],
                transition: { duration: 1.5, repeat: Infinity },
              }
            : {}
        }
      />
      <span className="capitalize">{status}</span>
    </motion.div>
  );
}

function MessageNotification({ message }: { message: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -50 }}
      className="fixed bottom-4 right-4 bg-linkedin-500 text-white px-6 py-3 rounded-lg shadow-lg"
    >
      <p className="text-sm font-medium">{message}</p>
    </motion.div>
  );
}

function LoadingState() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          className="inline-block"
        >
          <Activity size={48} className="text-linkedin-500" />
        </motion.div>
        <p className="mt-4 text-gray-600">Loading agent activity...</p>
      </div>
    </div>
  );
}
