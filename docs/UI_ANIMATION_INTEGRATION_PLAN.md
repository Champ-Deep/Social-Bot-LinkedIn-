# GSAP & Motion.dev Integration Plan
## Interactive UI Elements for LinkedIn Automation Dashboard

---

## Executive Summary

This document outlines how to integrate **GSAP (GreenSock Animation Platform)** and **Motion.dev** (Framer Motion) to create interactive UI elements for the LinkedIn automation dashboard, working seamlessly with the existing FastAPI backend.

### Current State
- ✅ Robust FastAPI REST API (`/campaigns`, `/auth`, etc.)
- ✅ Real-time updates via Redis pub/sub
- ✅ Agent orchestration system
- ❌ No frontend UI implemented yet

### Recommended Tech Stack
- **Frontend Framework**: React 18+ with TypeScript
- **Animation Libraries**:
  - **GSAP** for complex timelines, scroll animations, and SVG morphing
  - **Framer Motion** for component-based animations and gestures
- **State Management**: React Query + Zustand
- **Styling**: Tailwind CSS + shadcn/ui components
- **Real-time**: WebSocket or Server-Sent Events (SSE)

---

## 1. GSAP vs Motion.dev (Framer Motion)

### When to Use GSAP

**Best For:**
- Complex timeline animations
- Scroll-triggered animations (ScrollTrigger plugin)
- SVG path morphing and drawing
- Physics-based animations
- Performance-critical animations (60fps+ guaranteed)
- Precise control over easing and sequencing

**Use Cases in This Project:**
```javascript
// Campaign progress bar with smooth easing
gsap.to(".progress-bar", {
  width: "75%",
  duration: 1.5,
  ease: "power2.out"
});

// Scroll-triggered agent activity visualization
ScrollTrigger.create({
  trigger: ".agent-timeline",
  start: "top center",
  animation: gsap.from(".agent-card", {
    opacity: 0,
    y: 50,
    stagger: 0.2
  })
});

// SVG morphing for campaign status icons
gsap.to("#status-icon", {
  morphSVG: "#completed-icon",
  duration: 0.8,
  ease: "elastic.out(1, 0.5)"
});
```

### When to Use Framer Motion

**Best For:**
- React component animations
- Layout animations (automatic position transitions)
- Gesture-based interactions (drag, hover, tap)
- Page transitions
- Declarative animation syntax
- Variants system for complex state animations

**Use Cases in This Project:**
```jsx
// Campaign card with hover effects
<motion.div
  whileHover={{ scale: 1.02, y: -5 }}
  whileTap={{ scale: 0.98 }}
  transition={{ type: "spring", stiffness: 300 }}
>
  <CampaignCard />
</motion.div>

// Page transitions
<motion.div
  initial={{ opacity: 0, x: -20 }}
  animate={{ opacity: 1, x: 0 }}
  exit={{ opacity: 0, x: 20 }}
  transition={{ duration: 0.3 }}
>
  <CampaignDetails />
</motion.div>

// Collapsible task list
<motion.div
  animate={{ height: isOpen ? "auto" : 0 }}
  transition={{ duration: 0.3 }}
>
  <TaskList tasks={tasks} />
</motion.div>
```

### Recommended Hybrid Approach

**Use BOTH libraries for optimal results:**
- **Framer Motion**: Component-level interactions, page transitions, layout animations
- **GSAP**: Complex timelines, scroll effects, data visualizations, SVG animations

---

## 2. UI Architecture & Navigation

### Proposed Page Structure

```
/                           # Dashboard Home (Campaign Overview)
  ├── /campaigns            # Campaign List
  │   ├── /campaigns/:id    # Campaign Details
  │   └── /campaigns/new    # Create Campaign
  ├── /agents               # Agent Activity Monitor
  │   ├── /agents/:id       # Individual Agent Status
  │   └── /agents/logs      # Agent Logs & Events
  ├── /accounts             # LinkedIn Accounts
  ├── /analytics            # Performance Analytics
  └── /settings             # User Settings
```

### Navigation with Animations

#### Option 1: Framer Motion Page Transitions

```tsx
// App.tsx
import { AnimatePresence, motion } from 'framer-motion';
import { Routes, Route, useLocation } from 'react-router-dom';

const pageVariants = {
  initial: { opacity: 0, x: -20 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: 20 }
};

function App() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={
          <motion.div
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.3 }}
          >
            <Dashboard />
          </motion.div>
        } />
        {/* More routes... */}
      </Routes>
    </AnimatePresence>
  );
}
```

#### Option 2: GSAP Page Transitions (More Control)

```tsx
// Use GSAP for more complex transitions
import gsap from 'gsap';
import { useEffect, useRef } from 'react';

function CampaignDetails() {
  const containerRef = useRef(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.timeline()
        .from(".header", { y: -30, opacity: 0, duration: 0.4 })
        .from(".stats-card", {
          y: 20,
          opacity: 0,
          stagger: 0.1,
          duration: 0.3
        }, "-=0.2")
        .from(".task-list", { opacity: 0, duration: 0.3 }, "-=0.1");
    }, containerRef);

    return () => ctx.revert(); // Cleanup
  }, []);

  return <div ref={containerRef}>{/* content */}</div>;
}
```

---

## 3. Interactive UI Elements

### A. Campaign Cards (List View)

**Framer Motion Implementation:**

```tsx
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';

interface Campaign {
  id: string;
  name: string;
  status: 'draft' | 'running' | 'paused' | 'completed';
  progress: {
    total_tasks: number;
    completed_tasks: number;
    failed_tasks: number;
  };
}

const statusColors = {
  draft: 'bg-gray-500',
  running: 'bg-blue-500',
  paused: 'bg-yellow-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500'
};

function CampaignCard({ campaign }: { campaign: Campaign }) {
  const progress = (campaign.progress.completed_tasks / campaign.progress.total_tasks) * 100;

  return (
    <motion.div
      layout // Automatic layout transitions
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.9 }}
      whileHover={{
        scale: 1.02,
        boxShadow: "0 10px 30px rgba(0,0,0,0.1)"
      }}
      whileTap={{ scale: 0.98 }}
      className="bg-white rounded-lg p-6 cursor-pointer"
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
    >
      {/* Status Badge */}
      <motion.div
        className={`inline-block px-3 py-1 rounded-full text-white text-sm ${statusColors[campaign.status]}`}
        animate={campaign.status === 'running' ? {
          scale: [1, 1.05, 1],
          transition: { repeat: Infinity, duration: 2 }
        } : {}}
      >
        {campaign.status}
      </motion.div>

      {/* Campaign Name */}
      <h3 className="text-xl font-bold mt-4">{campaign.name}</h3>

      {/* Animated Progress Bar */}
      <div className="mt-4 bg-gray-200 rounded-full h-2 overflow-hidden">
        <motion.div
          className="bg-blue-500 h-full"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 1, ease: "easeOut" }}
        />
      </div>

      {/* Stats */}
      <div className="mt-4 grid grid-cols-3 gap-4">
        <Stat label="Total" value={campaign.progress.total_tasks} />
        <Stat label="Completed" value={campaign.progress.completed_tasks} />
        <Stat label="Failed" value={campaign.progress.failed_tasks} />
      </div>
    </motion.div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.2 }}
    >
      <p className="text-gray-500 text-sm">{label}</p>
      <motion.p
        className="text-2xl font-bold"
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", stiffness: 200, delay: 0.3 }}
      >
        {value}
      </motion.p>
    </motion.div>
  );
}
```

**API Integration:**

```tsx
import { useQuery } from '@tanstack/react-query';

function CampaignList() {
  const { data, isLoading } = useQuery({
    queryKey: ['campaigns'],
    queryFn: async () => {
      const response = await fetch('/campaigns', {
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`
        }
      });
      return response.json();
    },
    refetchInterval: 5000 // Real-time updates every 5s
  });

  if (isLoading) return <LoadingSpinner />;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <AnimatePresence>
        {data?.items.map((campaign) => (
          <CampaignCard key={campaign.id} campaign={campaign} />
        ))}
      </AnimatePresence>
    </div>
  );
}
```

---

### B. Real-Time Agent Activity Visualization

**GSAP Timeline Animation:**

```tsx
import { useEffect, useRef } from 'react';
import gsap from 'gsap';

interface Agent {
  id: string;
  name: string;
  status: 'idle' | 'processing' | 'waiting';
  current_task?: string;
}

function AgentActivityMonitor({ agents }: { agents: Agent[] }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const ctx = gsap.context(() => {
      // Animate agent cards in sequence
      gsap.from(".agent-card", {
        opacity: 0,
        y: 50,
        stagger: 0.1,
        duration: 0.5,
        ease: "power2.out"
      });

      // Pulsing animation for active agents
      gsap.to(".agent-card.processing", {
        boxShadow: "0 0 20px rgba(59, 130, 246, 0.5)",
        duration: 1,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut"
      });

      // Message flow animation
      gsap.to(".message-dot", {
        x: "100vw",
        duration: 3,
        repeat: -1,
        ease: "none",
        stagger: 0.5
      });
    }, containerRef);

    return () => ctx.revert();
  }, [agents]);

  return (
    <div ref={containerRef} className="space-y-4">
      {agents.map((agent) => (
        <div
          key={agent.id}
          className={`agent-card ${agent.status} bg-white rounded-lg p-6 shadow-md`}
        >
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-bold">{agent.name}</h4>
              <p className="text-sm text-gray-500">{agent.current_task || 'Idle'}</p>
            </div>
            <StatusIndicator status={agent.status} />
          </div>
        </div>
      ))}

      {/* Message Flow Visualization */}
      <svg className="w-full h-2">
        <circle className="message-dot" cx="10" cy="4" r="3" fill="#3b82f6" />
      </svg>
    </div>
  );
}

function StatusIndicator({ status }: { status: string }) {
  return (
    <motion.div
      className={`w-3 h-3 rounded-full ${
        status === 'processing' ? 'bg-blue-500' :
        status === 'waiting' ? 'bg-yellow-500' :
        'bg-gray-300'
      }`}
      animate={status === 'processing' ? {
        scale: [1, 1.3, 1],
        transition: { repeat: Infinity, duration: 1.5 }
      } : {}}
    />
  );
}
```

---

### C. Campaign Creation Flow (Multi-Step Form)

**Framer Motion Step Transitions:**

```tsx
import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';

const steps = [
  { id: 'basic', title: 'Basic Info' },
  { id: 'targets', title: 'Target URLs' },
  { id: 'actions', title: 'Actions' },
  { id: 'schedule', title: 'Schedule' }
];

function CreateCampaignFlow() {
  const [currentStep, setCurrentStep] = useState(0);
  const [direction, setDirection] = useState(1);

  const variants = {
    enter: (direction: number) => ({
      x: direction > 0 ? 300 : -300,
      opacity: 0
    }),
    center: {
      x: 0,
      opacity: 1
    },
    exit: (direction: number) => ({
      x: direction > 0 ? -300 : 300,
      opacity: 0
    })
  };

  const nextStep = () => {
    setDirection(1);
    setCurrentStep((prev) => Math.min(prev + 1, steps.length - 1));
  };

  const prevStep = () => {
    setDirection(-1);
    setCurrentStep((prev) => Math.max(prev - 1, 0));
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Progress Indicator */}
      <div className="flex justify-between mb-8">
        {steps.map((step, index) => (
          <div key={step.id} className="flex-1">
            <motion.div
              className={`h-2 rounded-full ${
                index <= currentStep ? 'bg-blue-500' : 'bg-gray-200'
              }`}
              initial={{ scaleX: 0 }}
              animate={{ scaleX: index <= currentStep ? 1 : 0 }}
              transition={{ duration: 0.3 }}
            />
            <p className="text-sm mt-2 text-center">{step.title}</p>
          </div>
        ))}
      </div>

      {/* Step Content */}
      <AnimatePresence mode="wait" custom={direction}>
        <motion.div
          key={currentStep}
          custom={direction}
          variants={variants}
          initial="enter"
          animate="center"
          exit="exit"
          transition={{ type: "tween", duration: 0.3 }}
        >
          <StepContent step={steps[currentStep].id} />
        </motion.div>
      </AnimatePresence>

      {/* Navigation Buttons */}
      <div className="flex justify-between mt-8">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={prevStep}
          disabled={currentStep === 0}
          className="px-6 py-2 rounded-lg bg-gray-200"
        >
          Previous
        </motion.button>

        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={nextStep}
          disabled={currentStep === steps.length - 1}
          className="px-6 py-2 rounded-lg bg-blue-500 text-white"
        >
          Next
        </motion.button>
      </div>
    </div>
  );
}
```

---

### D. Drag-and-Drop Target URL Manager

**Framer Motion Drag Gestures:**

```tsx
import { motion, Reorder } from 'framer-motion';
import { useState } from 'react';

function TargetURLManager() {
  const [urls, setUrls] = useState([
    { id: '1', url: 'https://linkedin.com/in/user1' },
    { id: '2', url: 'https://linkedin.com/in/user2' },
    { id: '3', url: 'https://linkedin.com/in/user3' }
  ]);

  return (
    <Reorder.Group axis="y" values={urls} onReorder={setUrls}>
      {urls.map((item) => (
        <Reorder.Item
          key={item.id}
          value={item}
          className="bg-white p-4 mb-2 rounded-lg shadow cursor-move"
        >
          <motion.div
            whileHover={{ scale: 1.02 }}
            whileDrag={{ scale: 1.05, boxShadow: "0 10px 30px rgba(0,0,0,0.2)" }}
            className="flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <GripVertical className="text-gray-400" />
              <span>{item.url}</span>
            </div>

            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={() => setUrls(urls.filter(u => u.id !== item.id))}
              className="text-red-500"
            >
              <X size={20} />
            </motion.button>
          </motion.div>
        </Reorder.Item>
      ))}
    </Reorder.Group>
  );
}
```

---

### E. Live Task Progress Visualization

**GSAP + SVG Animation:**

```tsx
import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { DrawSVGPlugin } from 'gsap/DrawSVGPlugin';

gsap.registerPlugin(DrawSVGPlugin);

function TaskProgressVisualization({ tasks }: { tasks: Task[] }) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current) return;

    const ctx = gsap.context(() => {
      // Animate SVG path drawing
      gsap.from(".progress-path", {
        drawSVG: "0%",
        duration: 2,
        ease: "power2.inOut"
      });

      // Animate data points
      gsap.from(".data-point", {
        scale: 0,
        opacity: 0,
        stagger: 0.1,
        duration: 0.5,
        ease: "back.out(1.7)"
      });

      // Pulse completed tasks
      gsap.to(".completed-marker", {
        scale: 1.2,
        opacity: 0.5,
        duration: 1,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut"
      });
    }, svgRef);

    return () => ctx.revert();
  }, [tasks]);

  return (
    <svg ref={svgRef} viewBox="0 0 800 400" className="w-full">
      {/* Progress line */}
      <path
        className="progress-path"
        d="M 50 200 Q 200 100, 400 150 T 750 180"
        stroke="#3b82f6"
        strokeWidth="3"
        fill="none"
      />

      {/* Task markers */}
      {tasks.map((task, i) => (
        <circle
          key={task.id}
          className={`data-point ${task.status === 'completed' ? 'completed-marker' : ''}`}
          cx={50 + (i * 150)}
          cy={200 - (Math.random() * 50)}
          r="8"
          fill={task.status === 'completed' ? '#10b981' : task.status === 'failed' ? '#ef4444' : '#6b7280'}
        />
      ))}
    </svg>
  );
}
```

---

## 4. Scroll-Based Interactions

**GSAP ScrollTrigger for Dashboard:**

```tsx
import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

function Dashboard() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const ctx = gsap.context(() => {
      // Parallax effect for header
      gsap.to(".dashboard-header", {
        y: -50,
        opacity: 0.5,
        scrollTrigger: {
          trigger: ".dashboard-header",
          start: "top top",
          end: "bottom top",
          scrub: true
        }
      });

      // Reveal campaign cards on scroll
      gsap.from(".campaign-card", {
        y: 100,
        opacity: 0,
        stagger: 0.2,
        scrollTrigger: {
          trigger: ".campaigns-section",
          start: "top center",
          end: "center center",
          toggleActions: "play none none reverse"
        }
      });

      // Pin agent activity monitor while scrolling
      ScrollTrigger.create({
        trigger: ".agent-monitor",
        start: "top top",
        end: "bottom bottom",
        pin: ".agent-sidebar",
        pinSpacing: false
      });
    }, containerRef);

    return () => ctx.revert();
  }, []);

  return (
    <div ref={containerRef}>
      <div className="dashboard-header">
        <h1>LinkedIn Automation Dashboard</h1>
      </div>

      <div className="campaigns-section">
        {/* Campaign cards */}
      </div>

      <div className="agent-monitor">
        <div className="agent-sidebar">
          {/* Pinned sidebar */}
        </div>
      </div>
    </div>
  );
}
```

---

## 5. Real-Time Updates Integration

### WebSocket Connection for Live Updates

```tsx
import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

function useRealtimeUpdates() {
  const queryClient = useQueryClient();
  const [socket, setSocket] = useState<WebSocket | null>(null);

  useEffect(() => {
    // Connect to FastAPI WebSocket endpoint
    const ws = new WebSocket('ws://localhost:8000/ws/campaigns');

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      // Animate update
      if (data.type === 'CAMPAIGN_UPDATE') {
        // Invalidate query to refetch
        queryClient.invalidateQueries(['campaigns', data.campaign_id]);

        // Trigger animation
        const element = document.querySelector(`[data-campaign-id="${data.campaign_id}"]`);
        if (element) {
          gsap.from(element, {
            backgroundColor: '#dbeafe',
            duration: 0.5,
            clearProps: 'backgroundColor'
          });
        }
      }

      if (data.type === 'TASK_COMPLETED') {
        // Confetti animation on task completion
        confetti({
          particleCount: 100,
          spread: 70,
          origin: { y: 0.6 }
        });
      }
    };

    setSocket(ws);

    return () => ws.close();
  }, [queryClient]);

  return socket;
}
```

---

## 6. Performance Optimization

### Code Splitting for Animations

```tsx
// Lazy load GSAP plugins only when needed
import { lazy, Suspense } from 'react';

const ScrollAnimations = lazy(() => import('./components/ScrollAnimations'));
const SVGAnimations = lazy(() => import('./components/SVGAnimations'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <ScrollAnimations />
      <SVGAnimations />
    </Suspense>
  );
}
```

### GPU Acceleration

```tsx
// Use will-change and transform for better performance
const cardVariants = {
  hover: {
    scale: 1.05,
    rotateY: 5, // 3D transform for GPU acceleration
    transition: {
      type: "spring",
      stiffness: 300
    }
  }
};

<motion.div
  variants={cardVariants}
  whileHover="hover"
  style={{ willChange: 'transform' }} // Hint to browser
>
  <CampaignCard />
</motion.div>
```

---

## 7. Accessibility Considerations

### Reduced Motion Support

```tsx
import { useReducedMotion } from 'framer-motion';

function AnimatedComponent() {
  const shouldReduceMotion = useReducedMotion();

  return (
    <motion.div
      animate={{
        scale: shouldReduceMotion ? 1 : [1, 1.2, 1],
        transition: shouldReduceMotion
          ? { duration: 0 }
          : { duration: 2, repeat: Infinity }
      }}
    >
      Content
    </motion.div>
  );
}
```

### Keyboard Navigation

```tsx
function InteractiveCard() {
  return (
    <motion.div
      tabIndex={0}
      role="button"
      aria-label="Campaign card"
      whileFocus={{ scale: 1.02, boxShadow: "0 0 0 3px #3b82f6" }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          // Handle activation
        }
      }}
    >
      <CampaignCard />
    </motion.div>
  );
}
```

---

## 8. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Set up React + TypeScript + Vite
- [ ] Install GSAP, Framer Motion, React Query
- [ ] Create API client with authentication
- [ ] Build basic layout with Tailwind CSS
- [ ] Implement routing with React Router

### Phase 2: Core UI Components (Week 3-4)
- [ ] Campaign list with Framer Motion cards
- [ ] Campaign details page with GSAP timeline
- [ ] Multi-step campaign creation form
- [ ] Real-time agent activity monitor

### Phase 3: Advanced Interactions (Week 5-6)
- [ ] Scroll-triggered animations (GSAP ScrollTrigger)
- [ ] Drag-and-drop URL manager
- [ ] SVG progress visualizations
- [ ] WebSocket integration for live updates

### Phase 4: Polish & Optimization (Week 7-8)
- [ ] Performance optimization (code splitting, memoization)
- [ ] Accessibility improvements (ARIA labels, keyboard nav)
- [ ] Responsive design refinements
- [ ] Error boundaries and loading states

---

## 9. File Structure

```
frontend/
├── public/
├── src/
│   ├── api/
│   │   ├── client.ts              # Axios/Fetch client
│   │   └── endpoints/
│   │       ├── campaigns.ts       # Campaign API calls
│   │       └── agents.ts          # Agent API calls
│   ├── components/
│   │   ├── campaigns/
│   │   │   ├── CampaignCard.tsx   # Framer Motion card
│   │   │   ├── CampaignList.tsx   # Grid layout
│   │   │   └── CreateCampaign.tsx # Multi-step form
│   │   ├── agents/
│   │   │   ├── AgentMonitor.tsx   # GSAP timeline
│   │   │   └── AgentCard.tsx      # Status indicator
│   │   └── ui/
│   │       ├── Button.tsx         # shadcn/ui components
│   │       ├── Card.tsx
│   │       └── Progress.tsx
│   ├── hooks/
│   │   ├── useCampaigns.ts        # React Query hooks
│   │   ├── useRealtimeUpdates.ts  # WebSocket hook
│   │   └── useScrollAnimation.ts  # GSAP hook
│   ├── pages/
│   │   ├── Dashboard.tsx          # Main dashboard
│   │   ├── CampaignDetails.tsx    # Detail view
│   │   └── AgentActivity.tsx      # Agent monitor
│   ├── store/
│   │   └── useStore.ts            # Zustand store
│   ├── App.tsx
│   └── main.tsx
├── package.json
└── vite.config.ts
```

---

## 10. Installation Commands

```bash
# Create React app with Vite
npm create vite@latest frontend -- --template react-ts
cd frontend

# Install dependencies
npm install

# Animation libraries
npm install gsap framer-motion

# State management & data fetching
npm install @tanstack/react-query zustand

# Routing
npm install react-router-dom

# UI components
npm install tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Utilities
npm install clsx tailwind-merge
npm install lucide-react # Icons

# Development tools
npm install -D @types/node
```

---

## Summary

### GSAP Use Cases
✅ Complex timelines (agent activity)
✅ Scroll animations (dashboard parallax)
✅ SVG morphing (status icons)
✅ Data visualizations (progress charts)

### Framer Motion Use Cases
✅ Component animations (cards, buttons)
✅ Layout transitions (page navigation)
✅ Gesture interactions (drag, hover, tap)
✅ Variants system (state-based animations)

### API Integration Points
- Campaign list: `GET /campaigns` → Animated cards
- Real-time updates: WebSocket → GSAP flash animations
- Task progress: `GET /campaigns/:id/status` → SVG visualizations
- Agent activity: Redis pub/sub → Timeline animations

### Next Steps
1. Choose frontend framework (recommended: React + TypeScript)
2. Set up project structure
3. Install GSAP + Framer Motion
4. Build component library with animations
5. Integrate with existing FastAPI backend
6. Add WebSocket for real-time updates

---

**Questions? Need specific code examples?** Let me know which interactive element you'd like to implement first!
