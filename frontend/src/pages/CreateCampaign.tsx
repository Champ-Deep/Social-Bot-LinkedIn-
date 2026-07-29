import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  FileText,
  Target,
  Settings,
  Calendar,
  Plus,
  X,
  ThumbsUp,
  MessageSquare,
  Share2,
  UserPlus,
} from 'lucide-react';
import { campaignApi } from '@/lib/api';
import type { CampaignCreate } from '@/types';
import { clsx } from 'clsx';

interface FormData {
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
  priority: number;
  scheduled_start?: string;
}

const steps = [
  {
    id: 1,
    title: 'Basic Info',
    subtitle: 'Campaign name and description',
    icon: FileText,
  },
  {
    id: 2,
    title: 'Target URLs',
    subtitle: 'LinkedIn profiles or posts',
    icon: Target,
  },
  {
    id: 3,
    title: 'Actions',
    subtitle: 'Choose automation actions',
    icon: Settings,
  },
  {
    id: 4,
    title: 'Schedule',
    subtitle: 'Set priority and timing',
    icon: Calendar,
  },
];

export function CreateCampaign() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [currentStep, setCurrentStep] = useState(1);
  const [direction, setDirection] = useState(1);

  const [formData, setFormData] = useState<FormData>({
    name: '',
    description: '',
    target_urls: [],
    account_ids: ['default-account'], // TODO: Fetch actual accounts
    actions: {
      like: true,
      comment: false,
      share: false,
      follow: false,
    },
    priority: 2,
  });

  const createMutation = useMutation({
    mutationFn: (data: CampaignCreate) => campaignApi.create(data),
    onSuccess: (campaign) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      navigate(`/campaigns/${campaign.id}`);
    },
  });

  const nextStep = () => {
    if (currentStep < steps.length) {
      setDirection(1);
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setDirection(-1);
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = () => {
    createMutation.mutate(formData);
  };

  const isStepValid = () => {
    switch (currentStep) {
      case 1:
        return formData.name.trim() !== '' && formData.description.trim() !== '';
      case 2:
        return formData.target_urls.length > 0;
      case 3:
        return Object.values(formData.actions).some((v) => v);
      case 4:
        return true;
      default:
        return false;
    }
  };

  const slideVariants = {
    enter: (direction: number) => ({
      x: direction > 0 ? 300 : -300,
      opacity: 0,
    }),
    center: {
      x: 0,
      opacity: 1,
    },
    exit: (direction: number) => ({
      x: direction > 0 ? -300 : 300,
      opacity: 0,
    }),
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/campaigns')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft size={20} />
            Back to Campaigns
          </button>

          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Create New Campaign
          </h1>
          <p className="text-gray-600">
            Set up your LinkedIn automation campaign in a few steps
          </p>
        </div>

        {/* Progress Indicator */}
        <div className="mb-8">
          <div className="flex justify-between">
            {steps.map((step, index) => {
              const isActive = currentStep === step.id;
              const isCompleted = currentStep > step.id;
              const Icon = step.icon;

              return (
                <div key={step.id} className="flex-1">
                  <div className="flex items-center">
                    {/* Line */}
                    {index > 0 && (
                      <div className="flex-1 h-1 mx-2">
                        <motion.div
                          className="h-full bg-gray-200 rounded-full overflow-hidden"
                          initial={false}
                        >
                          <motion.div
                            className="h-full bg-linkedin-500"
                            initial={{ width: 0 }}
                            animate={{ width: isCompleted ? '100%' : '0%' }}
                            transition={{ duration: 0.3 }}
                          />
                        </motion.div>
                      </div>
                    )}

                    {/* Step Indicator */}
                    <div className="flex flex-col items-center">
                      <motion.div
                        className={clsx(
                          'w-12 h-12 rounded-full flex items-center justify-center',
                          'border-2 transition-colors duration-300',
                          isActive || isCompleted
                            ? 'bg-linkedin-500 border-linkedin-500 text-white'
                            : 'bg-white border-gray-300 text-gray-400'
                        )}
                        whileHover={{ scale: 1.1 }}
                      >
                        {isCompleted ? <Check size={24} /> : <Icon size={24} />}
                      </motion.div>

                      <div className="mt-2 text-center">
                        <p
                          className={clsx(
                            'text-sm font-medium',
                            isActive || isCompleted
                              ? 'text-gray-900'
                              : 'text-gray-500'
                          )}
                        >
                          {step.title}
                        </p>
                        <p className="text-xs text-gray-500 hidden md:block">
                          {step.subtitle}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Form Content */}
        <div className="bg-white rounded-xl shadow-md p-8 mb-6">
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={currentStep}
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ type: 'tween', duration: 0.3 }}
            >
              {currentStep === 1 && (
                <Step1BasicInfo formData={formData} setFormData={setFormData} />
              )}
              {currentStep === 2 && (
                <Step2TargetURLs formData={formData} setFormData={setFormData} />
              )}
              {currentStep === 3 && (
                <Step3Actions formData={formData} setFormData={setFormData} />
              )}
              {currentStep === 4 && (
                <Step4Schedule formData={formData} setFormData={setFormData} />
              )}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Navigation Buttons */}
        <div className="flex justify-between">
          {currentStep > 1 ? (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={prevStep}
              className="flex items-center gap-2 px-6 py-3 border-2 border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50"
            >
              <ArrowLeft size={20} />
              Previous
            </motion.button>
          ) : (
            <div />
          )}

          {currentStep < steps.length ? (
            <motion.button
              whileHover={{ scale: isStepValid() ? 1.05 : 1 }}
              whileTap={{ scale: isStepValid() ? 0.95 : 1 }}
              onClick={nextStep}
              disabled={!isStepValid()}
              className={clsx(
                'flex items-center gap-2 px-6 py-3 rounded-lg font-medium',
                isStepValid()
                  ? 'bg-linkedin-500 text-white hover:bg-linkedin-600'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              )}
            >
              Next
              <ArrowRight size={20} />
            </motion.button>
          ) : (
            <motion.button
              whileHover={{ scale: isStepValid() ? 1.05 : 1 }}
              whileTap={{ scale: isStepValid() ? 0.95 : 1 }}
              onClick={handleSubmit}
              disabled={!isStepValid() || createMutation.isPending}
              className={clsx(
                'flex items-center gap-2 px-6 py-3 rounded-lg font-medium',
                isStepValid() && !createMutation.isPending
                  ? 'bg-green-500 text-white hover:bg-green-600'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              )}
            >
              {createMutation.isPending ? (
                <>
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    className="w-5 h-5 border-2 border-white border-t-transparent rounded-full"
                  />
                  Creating...
                </>
              ) : (
                <>
                  <Check size={20} />
                  Create Campaign
                </>
              )}
            </motion.button>
          )}
        </div>
      </div>
    </div>
  );
}

// Step 1: Basic Info
function Step1BasicInfo({
  formData,
  setFormData,
}: {
  formData: FormData;
  setFormData: (data: FormData) => void;
}) {
  return (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Campaign Name *
        </label>
        <input
          type="text"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="e.g., Tech Industry Outreach Q1 2024"
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-linkedin-500 focus:border-transparent outline-none"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Description *
        </label>
        <textarea
          value={formData.description}
          onChange={(e) =>
            setFormData({ ...formData, description: e.target.value })
          }
          placeholder="Describe your campaign goals and target audience..."
          rows={6}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-linkedin-500 focus:border-transparent outline-none resize-none"
        />
      </div>
    </div>
  );
}

// Step 2: Target URLs
function Step2TargetURLs({
  formData,
  setFormData,
}: {
  formData: FormData;
  setFormData: (data: FormData) => void;
}) {
  const [newUrl, setNewUrl] = useState('');

  const addUrl = () => {
    if (newUrl.trim() && !formData.target_urls.includes(newUrl.trim())) {
      setFormData({
        ...formData,
        target_urls: [...formData.target_urls, newUrl.trim()],
      });
      setNewUrl('');
    }
  };

  const removeUrl = (url: string) => {
    setFormData({
      ...formData,
      target_urls: formData.target_urls.filter((u) => u !== url),
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Add Target URL
        </label>
        <div className="flex gap-2">
          <input
            type="url"
            value={newUrl}
            onChange={(e) => setNewUrl(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && addUrl()}
            placeholder="https://linkedin.com/in/username"
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-linkedin-500 focus:border-transparent outline-none"
          />
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={addUrl}
            className="px-6 py-3 bg-linkedin-500 text-white rounded-lg font-medium hover:bg-linkedin-600 flex items-center gap-2"
          >
            <Plus size={20} />
            Add
          </motion.button>
        </div>
      </div>

      {formData.target_urls.length > 0 && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Target URLs ({formData.target_urls.length})
          </label>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            <AnimatePresence mode="popLayout">
              {formData.target_urls.map((url) => (
                <motion.div
                  key={url}
                  layout
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200"
                >
                  <span className="text-sm text-gray-700 truncate">{url}</span>
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={() => removeUrl(url)}
                    className="text-red-500 hover:text-red-700"
                  >
                    <X size={20} />
                  </motion.button>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>
      )}
    </div>
  );
}

// Step 3: Actions
function Step3Actions({
  formData,
  setFormData,
}: {
  formData: FormData;
  setFormData: (data: FormData) => void;
}) {
  const actions = [
    {
      key: 'like' as const,
      icon: ThumbsUp,
      label: 'Like Posts',
      description: 'Automatically like target posts',
      color: 'bg-blue-500',
    },
    {
      key: 'comment' as const,
      icon: MessageSquare,
      label: 'Comment',
      description: 'Leave AI-generated comments',
      color: 'bg-green-500',
    },
    {
      key: 'share' as const,
      icon: Share2,
      label: 'Share',
      description: 'Share posts to your network',
      color: 'bg-purple-500',
    },
    {
      key: 'follow' as const,
      icon: UserPlus,
      label: 'Follow',
      description: 'Follow target profiles',
      color: 'bg-orange-500',
    },
  ];

  const toggleAction = (key: keyof FormData['actions']) => {
    setFormData({
      ...formData,
      actions: {
        ...formData.actions,
        [key]: !formData.actions[key],
      },
    });
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600 mb-4">
        Select the actions you want to automate
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {actions.map((action) => {
          const Icon = action.icon;
          const isActive = formData.actions[action.key];

          return (
            <motion.button
              key={action.key}
              onClick={() => toggleAction(action.key)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={clsx(
                'p-6 rounded-xl border-2 text-left transition-all',
                isActive
                  ? 'border-linkedin-500 bg-linkedin-50'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              )}
            >
              <div className="flex items-start gap-4">
                <div
                  className={clsx(
                    'w-12 h-12 rounded-lg flex items-center justify-center text-white',
                    action.color
                  )}
                >
                  <Icon size={24} />
                </div>

                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-gray-900">
                      {action.label}
                    </h3>
                    {isActive && (
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className="w-6 h-6 bg-linkedin-500 rounded-full flex items-center justify-center"
                      >
                        <Check size={16} className="text-white" />
                      </motion.div>
                    )}
                  </div>
                  <p className="text-sm text-gray-600">{action.description}</p>
                </div>
              </div>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}

// Step 4: Schedule
function Step4Schedule({
  formData,
  setFormData,
}: {
  formData: FormData;
  setFormData: (data: FormData) => void;
}) {
  const priorities = [
    { value: 1, label: 'Low', description: 'Run when resources available' },
    { value: 2, label: 'Normal', description: 'Standard priority' },
    { value: 3, label: 'High', description: 'Execute as soon as possible' },
  ];

  return (
    <div className="space-y-6">
      {/* Priority */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-4">
          Campaign Priority
        </label>
        <div className="grid grid-cols-3 gap-4">
          {priorities.map((priority) => (
            <motion.button
              key={priority.value}
              onClick={() =>
                setFormData({ ...formData, priority: priority.value })
              }
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={clsx(
                'p-4 rounded-lg border-2 text-center transition-all',
                formData.priority === priority.value
                  ? 'border-linkedin-500 bg-linkedin-50'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              )}
            >
              <h4 className="font-semibold text-gray-900 mb-1">
                {priority.label}
              </h4>
              <p className="text-xs text-gray-600">{priority.description}</p>
            </motion.button>
          ))}
        </div>
      </div>

      {/* Schedule Start (Optional) */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Scheduled Start (Optional)
        </label>
        <input
          type="datetime-local"
          value={formData.scheduled_start || ''}
          onChange={(e) =>
            setFormData({ ...formData, scheduled_start: e.target.value })
          }
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-linkedin-500 focus:border-transparent outline-none"
        />
        <p className="text-sm text-gray-500 mt-2">
          Leave empty to start immediately when campaign is activated
        </p>
      </div>

      {/* Summary */}
      <div className="mt-8 p-6 bg-gray-50 rounded-lg border border-gray-200">
        <h3 className="font-semibold text-gray-900 mb-4">Campaign Summary</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">Name:</span>
            <span className="font-medium">{formData.name || '-'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Target URLs:</span>
            <span className="font-medium">{formData.target_urls.length}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Actions:</span>
            <span className="font-medium">
              {Object.values(formData.actions).filter(Boolean).length}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Priority:</span>
            <span className="font-medium">
              {priorities.find((p) => p.value === formData.priority)?.label}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
