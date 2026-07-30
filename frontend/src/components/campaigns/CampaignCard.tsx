import { motion } from 'framer-motion';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Play,
  Pause,
  Calendar,
  Target,
  CheckCircle2,
  XCircle,
  Loader2,
} from 'lucide-react';
import { format } from 'date-fns';
import type { Campaign } from '@/types';
import { campaignApi } from '@/lib/api';
import { clsx } from 'clsx';

interface CampaignCardProps {
  campaign: Campaign;
}

const statusConfig = {
  draft: {
    color: 'bg-gray-500',
    textColor: 'text-gray-700',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-200',
  },
  scheduled: {
    color: 'bg-purple-500',
    textColor: 'text-purple-700',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
  },
  running: {
    color: 'bg-blue-500',
    textColor: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
  },
  paused: {
    color: 'bg-yellow-500',
    textColor: 'text-yellow-700',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
  },
  completed: {
    color: 'bg-green-500',
    textColor: 'text-green-700',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
  },
  failed: {
    color: 'bg-red-500',
    textColor: 'text-red-700',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
  },
  cancelled: {
    color: 'bg-gray-400',
    textColor: 'text-gray-600',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-200',
  },
};

export function CampaignCard({ campaign }: CampaignCardProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const startMutation = useMutation({
    mutationFn: () => campaignApi.start(campaign.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });

  const pauseMutation = useMutation({
    mutationFn: () => campaignApi.pause(campaign.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });

  const progress =
    campaign.progress.total_tasks > 0
      ? (campaign.progress.completed_tasks / campaign.progress.total_tasks) * 100
      : 0;

  const isRunning = campaign.status === 'running';
  const config = statusConfig[campaign.status];
  const isLoading = startMutation.isPending || pauseMutation.isPending;

  const handleAction = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isRunning) {
      pauseMutation.mutate();
    } else if (campaign.status === 'draft' || campaign.status === 'paused') {
      startMutation.mutate();
    }
  };

  return (
    <motion.div
      layout
      layoutId={`campaign-${campaign.id}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.9 }}
      whileHover={{
        scale: 1.02,
        boxShadow: '0 20px 40px rgba(0, 0, 0, 0.12)',
        transition: { duration: 0.2 },
      }}
      whileTap={{ scale: 0.98 }}
      onClick={() => navigate(`/campaigns/${campaign.id}`)}
      className={clsx(
        'bg-white rounded-xl p-6 shadow-md cursor-pointer border-2',
        'transition-all duration-200',
        config.borderColor
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        {/* Status Badge */}
        <motion.div
          className={clsx(
            'inline-flex items-center gap-2 px-3 py-1 rounded-full text-white text-sm font-medium',
            config.color
          )}
          animate={
            isRunning
              ? {
                  scale: [1, 1.05, 1],
                  transition: { duration: 2, repeat: Infinity },
                }
              : {}
          }
        >
          {isRunning && (
            <motion.span
              className="w-2 h-2 bg-white rounded-full"
              animate={{
                opacity: [1, 0.3, 1],
                transition: { duration: 1.5, repeat: Infinity },
              }}
            />
          )}
          <span className="capitalize">{campaign.status}</span>
        </motion.div>

        {/* Date */}
        <div className="flex items-center gap-1 text-sm text-gray-500">
          <Calendar size={14} />
          <span>{format(new Date(campaign.created_at), 'MMM d, yyyy')}</span>
        </div>
      </div>

      {/* Campaign Info */}
      <h3 className="text-xl font-bold text-gray-900 mb-2 line-clamp-1">
        {campaign.name}
      </h3>
      <p className="text-gray-600 text-sm mb-4 line-clamp-2">
        {campaign.description}
      </p>

      {/* Actions Summary */}
      <div className="flex flex-wrap gap-2 mb-4">
        {campaign.actions.like && (
          <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium">
            👍 Like
          </span>
        )}
        {campaign.actions.comment && (
          <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-medium">
            💬 Comment
          </span>
        )}
        {campaign.actions.share && (
          <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs font-medium">
            🔄 Share
          </span>
        )}
        {campaign.actions.follow && (
          <span className="px-2 py-1 bg-orange-100 text-orange-700 rounded text-xs font-medium">
            ➕ Follow
          </span>
        )}
      </div>

      {/* Progress Bar */}
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
        <StatItem
          icon={<Target size={16} />}
          label="Total"
          value={campaign.progress.total_tasks}
          delay={0.1}
        />
        <StatItem
          icon={<CheckCircle2 size={16} />}
          label="Done"
          value={campaign.progress.completed_tasks}
          delay={0.2}
          color="text-green-600"
        />
        <StatItem
          icon={<XCircle size={16} />}
          label="Failed"
          value={campaign.progress.failed_tasks}
          delay={0.3}
          color="text-red-600"
        />
      </div>

      {/* Action Button */}
      <motion.button
        whileHover={{ scale: isLoading ? 1 : 1.05 }}
        whileTap={{ scale: isLoading ? 1 : 0.95 }}
        onClick={handleAction}
        disabled={isLoading || campaign.status === 'completed'}
        className={clsx(
          'w-full py-2 px-4 rounded-lg font-medium text-white',
          'transition-colors duration-200',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'flex items-center justify-center gap-2',
          isRunning
            ? 'bg-yellow-500 hover:bg-yellow-600'
            : campaign.status === 'completed'
            ? 'bg-gray-400'
            : 'bg-green-500 hover:bg-green-600'
        )}
      >
        {isLoading ? (
          <>
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            >
              <Loader2 size={18} />
            </motion.div>
            <span>Processing...</span>
          </>
        ) : isRunning ? (
          <>
            <Pause size={18} />
            <span>Pause Campaign</span>
          </>
        ) : campaign.status === 'completed' ? (
          <>
            <CheckCircle2 size={18} />
            <span>Completed</span>
          </>
        ) : (
          <>
            <Play size={18} />
            <span>Start Campaign</span>
          </>
        )}
      </motion.button>
    </motion.div>
  );
}

interface StatItemProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  delay?: number;
  color?: string;
}

function StatItem({ icon, label, value, delay = 0, color = 'text-gray-900' }: StatItemProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="text-center"
    >
      <div className="flex items-center justify-center gap-1 text-gray-500 mb-1">
        {icon}
        <p className="text-xs">{label}</p>
      </div>
      <motion.p
        className={clsx('text-2xl font-bold', color)}
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 200, delay: delay + 0.1 }}
      >
        {value}
      </motion.p>
    </motion.div>
  );
}
