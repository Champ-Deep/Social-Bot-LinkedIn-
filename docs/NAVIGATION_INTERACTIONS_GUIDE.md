# Navigation & Interactions Quick Reference
## How GSAP and Framer Motion Work with Your Current API

---

## Current API Endpoints → UI Navigation Mapping

### Your Existing Backend Routes

| API Endpoint | HTTP Method | UI Page | Animation Type |
|-------------|-------------|---------|----------------|
| `/campaigns` | GET | Campaign List | Framer Motion cards |
| `/campaigns/:id` | GET | Campaign Details | GSAP timeline entry |
| `/campaigns` | POST | Create Campaign Modal | Multi-step form transitions |
| `/campaigns/:id/start` | POST | Action trigger | Success animation |
| `/campaigns/:id/status` | GET | Progress indicator | Real-time bar animation |
| `/campaigns/:id/tasks` | GET | Task list | Staggered reveal |

---

## Navigation Flow with Animations

### 1. Dashboard → Campaign List

**User Action:** Clicks "View All Campaigns"

**API Call:**
```typescript
// src/api/endpoints/campaigns.ts
export async function getCampaigns(page = 1, pageSize = 20) {
  const response = await apiClient.get('/campaigns', {
    params: { page, page_size: pageSize }
  });
  return response.data;
}
```

**Framer Motion Navigation:**
```tsx
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

function Dashboard() {
  const navigate = useNavigate();

  return (
    <motion.button
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onClick={() => navigate('/campaigns')}
      className="px-6 py-3 bg-blue-500 text-white rounded-lg"
    >
      View All Campaigns
    </motion.button>
  );
}
```

**Page Transition:**
```tsx
// App.tsx with AnimatePresence
<AnimatePresence mode="wait">
  <Routes location={location} key={location.pathname}>
    <Route path="/campaigns" element={
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.3 }}
      >
        <CampaignList />
      </motion.div>
    } />
  </Routes>
</AnimatePresence>
```

---

### 2. Campaign List → Campaign Details

**User Action:** Clicks on a campaign card

**API Call:**
```typescript
export async function getCampaignById(id: string) {
  const response = await apiClient.get(`/campaigns/${id}`);
  return response.data;
}
```

**Interaction Flow:**

**Step 1: Card Click with Framer Motion**
```tsx
function CampaignCard({ campaign }) {
  const navigate = useNavigate();

  return (
    <motion.div
      layoutId={`campaign-${campaign.id}`} // Shared layout animation
      onClick={() => navigate(`/campaigns/${campaign.id}`)}
      whileHover={{
        scale: 1.02,
        boxShadow: "0 10px 30px rgba(0,0,0,0.15)"
      }}
      whileTap={{ scale: 0.98 }}
      className="cursor-pointer bg-white rounded-lg p-6"
    >
      <h3>{campaign.name}</h3>
      <StatusBadge status={campaign.status} />
    </motion.div>
  );
}
```

**Step 2: Details Page with GSAP Timeline**
```tsx
function CampaignDetails({ id }) {
  const containerRef = useRef(null);
  const { data: campaign } = useQuery(['campaign', id], () => getCampaignById(id));

  useEffect(() => {
    if (!campaign) return;

    const ctx = gsap.context(() => {
      const tl = gsap.timeline();

      tl.from('.header', {
        y: -30,
        opacity: 0,
        duration: 0.4
      })
      .from('.stats-grid > div', {
        y: 20,
        opacity: 0,
        stagger: 0.1,
        duration: 0.3
      }, '-=0.2')
      .from('.task-list', {
        opacity: 0,
        duration: 0.3
      });
    }, containerRef);

    return () => ctx.revert();
  }, [campaign]);

  return (
    <motion.div
      ref={containerRef}
      layoutId={`campaign-${id}`} // Matches card layoutId
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <div className="header">
        <h1>{campaign?.name}</h1>
      </div>

      <div className="stats-grid grid grid-cols-3 gap-4">
        <StatCard label="Total Tasks" value={campaign?.progress.total_tasks} />
        <StatCard label="Completed" value={campaign?.progress.completed_tasks} />
        <StatCard label="Failed" value={campaign?.progress.failed_tasks} />
      </div>

      <div className="task-list">
        <TaskList tasks={campaign?.tasks} />
      </div>
    </motion.div>
  );
}
```

---

### 3. Create Campaign Flow (Multi-Step Form)

**User Action:** Clicks "Create Campaign"

**API Call (Final Step):**
```typescript
export async function createCampaign(data: CampaignCreate) {
  const response = await apiClient.post('/campaigns', data);
  return response.data;
}
```

**Multi-Step Navigation:**

```tsx
const steps = [
  { id: 1, title: 'Basic Info', component: BasicInfoStep },
  { id: 2, title: 'Target URLs', component: TargetURLsStep },
  { id: 3, title: 'Actions', component: ActionsStep },
  { id: 4, title: 'Schedule', component: ScheduleStep }
];

function CreateCampaignWizard() {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState({});
  const [direction, setDirection] = useState(1);

  const nextStep = () => {
    setDirection(1);
    setCurrentStep(prev => prev + 1);
  };

  const prevStep = () => {
    setDirection(-1);
    setCurrentStep(prev => prev - 1);
  };

  const CurrentStepComponent = steps[currentStep - 1].component;

  return (
    <div className="max-w-3xl mx-auto">
      {/* Animated Progress Bar */}
      <div className="flex gap-2 mb-8">
        {steps.map((step) => (
          <motion.div
            key={step.id}
            className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden"
          >
            <motion.div
              className="h-full bg-blue-500"
              initial={{ width: 0 }}
              animate={{
                width: step.id <= currentStep ? '100%' : '0%'
              }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
            />
          </motion.div>
        ))}
      </div>

      {/* Step Content with Slide Transition */}
      <AnimatePresence mode="wait" custom={direction}>
        <motion.div
          key={currentStep}
          custom={direction}
          initial={{ x: direction > 0 ? 300 : -300, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: direction > 0 ? -300 : 300, opacity: 0 }}
          transition={{ type: 'tween', duration: 0.3 }}
        >
          <CurrentStepComponent
            data={formData}
            onChange={setFormData}
          />
        </motion.div>
      </AnimatePresence>

      {/* Navigation Buttons */}
      <div className="flex justify-between mt-8">
        {currentStep > 1 && (
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={prevStep}
            className="px-6 py-2 border rounded-lg"
          >
            Previous
          </motion.button>
        )}

        {currentStep < steps.length ? (
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={nextStep}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg ml-auto"
          >
            Next
          </motion.button>
        ) : (
          <SubmitButton formData={formData} />
        )}
      </div>
    </div>
  );
}
```

---

## Interactive Elements Breakdown

### 1. Campaign Status Badge (Pulsing Animation)

**API Response:**
```json
{
  "status": "running",
  "progress": {
    "total_tasks": 100,
    "completed_tasks": 45,
    "failed_tasks": 2
  }
}
```

**Framer Motion Implementation:**
```tsx
function StatusBadge({ status }: { status: CampaignStatus }) {
  const colors = {
    draft: 'bg-gray-500',
    running: 'bg-blue-500',
    paused: 'bg-yellow-500',
    completed: 'bg-green-500',
    failed: 'bg-red-500'
  };

  return (
    <motion.div
      className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-white ${colors[status]}`}
      animate={status === 'running' ? {
        scale: [1, 1.05, 1],
        transition: {
          duration: 2,
          repeat: Infinity,
          ease: 'easeInOut'
        }
      } : {}}
    >
      {status === 'running' && (
        <motion.span
          className="w-2 h-2 bg-white rounded-full"
          animate={{
            opacity: [1, 0.3, 1],
            transition: {
              duration: 1.5,
              repeat: Infinity
            }
          }}
        />
      )}
      <span className="capitalize">{status}</span>
    </motion.div>
  );
}
```

---

### 2. Progress Bar (Real-Time Updates)

**API Polling:**
```tsx
function CampaignProgress({ campaignId }: { campaignId: string }) {
  const { data } = useQuery(
    ['campaign-status', campaignId],
    () => getCampaignStatus(campaignId),
    {
      refetchInterval: 3000, // Poll every 3 seconds
      enabled: true
    }
  );

  const progressPercent = data
    ? (data.progress.completed_tasks / data.progress.total_tasks) * 100
    : 0;

  return (
    <div className="w-full">
      <div className="flex justify-between mb-2">
        <span className="text-sm font-medium">Progress</span>
        <motion.span
          key={progressPercent}
          initial={{ scale: 1.2, color: '#3b82f6' }}
          animate={{ scale: 1, color: '#000' }}
          transition={{ duration: 0.3 }}
          className="text-sm"
        >
          {Math.round(progressPercent)}%
        </motion.span>
      </div>

      <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-gradient-to-r from-blue-500 to-blue-600"
          initial={{ width: 0 }}
          animate={{ width: `${progressPercent}%` }}
          transition={{
            duration: 0.8,
            ease: 'easeOut'
          }}
        />
      </div>
    </div>
  );
}
```

---

### 3. Start/Pause Campaign (Action Buttons)

**API Calls:**
```typescript
export async function startCampaign(id: string) {
  const response = await apiClient.post(`/campaigns/${id}/start`);
  return response.data;
}

export async function pauseCampaign(id: string) {
  const response = await apiClient.post(`/campaigns/${id}/pause`);
  return response.data;
}
```

**Interactive Button with Loading State:**
```tsx
function CampaignActionButton({ campaign }: { campaign: Campaign }) {
  const queryClient = useQueryClient();
  const [isLoading, setIsLoading] = useState(false);

  const startMutation = useMutation(startCampaign, {
    onSuccess: () => {
      queryClient.invalidateQueries(['campaign', campaign.id]);
      // Success animation
      confetti({
        particleCount: 100,
        spread: 70,
        origin: { y: 0.6 }
      });
    }
  });

  const pauseMutation = useMutation(pauseCampaign, {
    onSuccess: () => {
      queryClient.invalidateQueries(['campaign', campaign.id]);
    }
  });

  const handleClick = () => {
    if (campaign.status === 'running') {
      pauseMutation.mutate(campaign.id);
    } else {
      startMutation.mutate(campaign.id);
    }
  };

  const isRunning = campaign.status === 'running';
  const isDisabled = startMutation.isLoading || pauseMutation.isLoading;

  return (
    <motion.button
      whileHover={!isDisabled ? { scale: 1.05 } : {}}
      whileTap={!isDisabled ? { scale: 0.95 } : {}}
      onClick={handleClick}
      disabled={isDisabled}
      className={`px-6 py-3 rounded-lg font-medium ${
        isRunning
          ? 'bg-yellow-500 text-white'
          : 'bg-green-500 text-white'
      }`}
    >
      <motion.span
        key={campaign.status}
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-2"
      >
        {isDisabled ? (
          <>
            <motion.div
              className="w-4 h-4 border-2 border-white border-t-transparent rounded-full"
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            />
            Loading...
          </>
        ) : isRunning ? (
          <>
            <Pause size={20} />
            Pause Campaign
          </>
        ) : (
          <>
            <Play size={20} />
            Start Campaign
          </>
        )}
      </motion.span>
    </motion.button>
  );
}
```

---

### 4. Task List with Staggered Animation

**API Response:**
```json
{
  "items": [
    {
      "id": "task-1",
      "target_url": "https://linkedin.com/in/user1",
      "status": "completed",
      "result": { "likes": 1, "comments": 1 }
    },
    {
      "id": "task-2",
      "target_url": "https://linkedin.com/in/user2",
      "status": "in_progress",
      "result": null
    }
  ]
}
```

**GSAP Stagger Animation:**
```tsx
function TaskList({ campaignId }: { campaignId: string }) {
  const listRef = useRef(null);
  const { data: tasks } = useQuery(
    ['campaign-tasks', campaignId],
    () => getCampaignTasks(campaignId)
  );

  useEffect(() => {
    if (!tasks || !listRef.current) return;

    const ctx = gsap.context(() => {
      gsap.from('.task-item', {
        x: -50,
        opacity: 0,
        stagger: 0.05, // 50ms delay between each item
        duration: 0.4,
        ease: 'power2.out'
      });
    }, listRef);

    return () => ctx.revert();
  }, [tasks]);

  return (
    <div ref={listRef} className="space-y-3">
      {tasks?.items.map((task) => (
        <div
          key={task.id}
          className="task-item bg-white p-4 rounded-lg shadow-sm flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <TaskStatusIcon status={task.status} />
            <span className="text-sm">{task.target_url}</span>
          </div>

          {task.status === 'completed' && task.result && (
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 200 }}
              className="flex gap-2 text-sm text-gray-500"
            >
              <span>👍 {task.result.likes}</span>
              <span>💬 {task.result.comments}</span>
            </motion.div>
          )}
        </div>
      ))}
    </div>
  );
}

function TaskStatusIcon({ status }: { status: TaskStatus }) {
  const icons = {
    pending: <Clock className="text-gray-400" size={20} />,
    in_progress: (
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
      >
        <Loader className="text-blue-500" size={20} />
      </motion.div>
    ),
    completed: <CheckCircle className="text-green-500" size={20} />,
    failed: <XCircle className="text-red-500" size={20} />
  };

  return icons[status];
}
```

---

### 5. Real-Time Updates (WebSocket Integration)

**Backend WebSocket (FastAPI):**
```python
# main.py
from fastapi import WebSocket

@app.websocket("/ws/campaigns/{campaign_id}")
async def campaign_websocket(websocket: WebSocket, campaign_id: str):
    await websocket.accept()

    # Subscribe to Redis pub/sub
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"campaign:{campaign_id}")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_json(message["data"])
    finally:
        await pubsub.unsubscribe(f"campaign:{campaign_id}")
```

**Frontend WebSocket Hook:**
```tsx
function useRealtimeProgress(campaignId: string) {
  const [progress, setProgress] = useState({ completed: 0, total: 0 });
  const queryClient = useQueryClient();

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/campaigns/${campaignId}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'TASK_COMPLETED') {
        // Update progress
        setProgress(prev => ({
          ...prev,
          completed: prev.completed + 1
        }));

        // Trigger celebration animation
        const element = document.querySelector(`[data-task-id="${data.task_id}"]`);
        if (element) {
          gsap.from(element, {
            scale: 1.2,
            backgroundColor: '#10b981',
            duration: 0.5,
            clearProps: 'backgroundColor'
          });
        }

        // Play sound (optional)
        new Audio('/sounds/task-complete.mp3').play();
      }

      // Invalidate cache to refetch data
      queryClient.invalidateQueries(['campaign-status', campaignId]);
    };

    return () => ws.close();
  }, [campaignId, queryClient]);

  return progress;
}
```

**Usage in Component:**
```tsx
function CampaignMonitor({ campaignId }: { campaignId: string }) {
  const progress = useRealtimeProgress(campaignId);

  return (
    <div>
      <h2>Live Progress</h2>
      <AnimatedNumber value={progress.completed} /> / {progress.total}

      <motion.div
        className="h-2 bg-gray-200 rounded-full overflow-hidden"
      >
        <motion.div
          className="h-full bg-green-500"
          animate={{
            width: `${(progress.completed / progress.total) * 100}%`
          }}
          transition={{ type: 'spring', stiffness: 50 }}
        />
      </motion.div>
    </div>
  );
}

// Animated number component
function AnimatedNumber({ value }: { value: number }) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    gsap.to({ val: displayValue }, {
      val: value,
      duration: 0.5,
      onUpdate: function() {
        setDisplayValue(Math.round(this.targets()[0].val));
      }
    });
  }, [value]);

  return <span>{displayValue}</span>;
}
```

---

## Navigation Patterns Summary

### 1. **List View → Detail View**
- **Animation**: Shared layout transition (Framer Motion `layoutId`)
- **API**: `GET /campaigns` → `GET /campaigns/:id`
- **User Experience**: Smooth morphing from card to full page

### 2. **Modal Overlays**
- **Animation**: Backdrop fade + modal scale
- **API**: Action endpoints (`POST /campaigns/:id/start`)
- **User Experience**: Non-intrusive confirmation dialogs

### 3. **Multi-Step Forms**
- **Animation**: Slide transitions between steps
- **API**: Final `POST /campaigns` on submit
- **User Experience**: Progressive disclosure of form fields

### 4. **Real-Time Updates**
- **Animation**: Flash/pulse on data change
- **API**: WebSocket or polling
- **User Experience**: Live feedback without page refresh

### 5. **Scroll-Based Reveals**
- **Animation**: GSAP ScrollTrigger
- **API**: Lazy loading with pagination
- **User Experience**: Progressive content loading

---

## Complete Navigation Example

Here's a full example showing how all pieces work together:

```tsx
// App.tsx - Main application with routing
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <AnimatedRoutes />
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

function AnimatedRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<PageWrapper><Dashboard /></PageWrapper>} />
        <Route path="/campaigns" element={<PageWrapper><CampaignList /></PageWrapper>} />
        <Route path="/campaigns/:id" element={<PageWrapper><CampaignDetails /></PageWrapper>} />
        <Route path="/agents" element={<PageWrapper><AgentMonitor /></PageWrapper>} />
      </Routes>
    </AnimatePresence>
  );
}

// Reusable page wrapper with animation
function PageWrapper({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
    >
      {children}
    </motion.div>
  );
}
```

---

## Key Takeaways

✅ **Framer Motion** handles React component-level interactions and page transitions
✅ **GSAP** powers complex timelines, scroll effects, and data visualizations
✅ **React Query** manages API state with automatic caching and invalidation
✅ **WebSocket** provides real-time updates with animated feedback
✅ **Layout animations** create seamless transitions between views
✅ **Stagger animations** reveal lists progressively for better UX

**Next Step**: Choose which interactive element to implement first, and I can provide the complete implementation code!
