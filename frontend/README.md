# LinkedIn Automation Dashboard

A modern, animated React dashboard for managing LinkedIn automation campaigns with real-time updates.

## 🚀 Features

### ✅ Completed Components

#### 1. **Campaign List with Animated Cards**
- Framer Motion card animations (hover, tap, layout)
- GSAP page entry animations with staggered reveals
- Real-time progress bars with smooth transitions
- Status badges with pulsing animations
- Filter by campaign status
- Search functionality
- Live WebSocket connection indicator

#### 2. **Multi-Step Campaign Creation Form**
- 4-step wizard with slide transitions
- Animated progress indicator
- Form validation at each step
- Drag-and-drop URL management (can be enhanced)
- Action selection with animated cards
- Campaign summary preview
- Success animations on submission

#### 3. **Real-Time WebSocket Updates**
- Automatic reconnection with exponential backoff
- Live campaign progress updates
- Task completion notifications
- Agent status changes
- React Query cache invalidation on updates

#### 4. **Agent Activity Monitor**
- Real-time agent status display
- GSAP timeline animations for agent cards
- Pulsing effects for active agents
- Activity statistics
- Progress bars for processing tasks
- Last activity timestamps
- Agent type-specific icons and colors

## 🎨 Animation Libraries

### Framer Motion
- Component-level animations (cards, buttons)
- Layout animations and shared layouts
- Page transitions with AnimatePresence
- Gesture interactions (hover, tap, drag)
- Variants system for complex state animations

### GSAP (GreenSock Animation Platform)
- Page entry animations with timelines
- Staggered reveals for lists
- Pulsing effects for active elements
- Box shadow animations
- Complex sequenced animations

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── campaigns/
│   │   │   └── CampaignCard.tsx      # Animated campaign card
│   │   └── Navigation.tsx             # App navigation bar
│   ├── hooks/
│   │   └── useWebSocket.ts            # WebSocket hook with reconnection
│   ├── lib/
│   │   └── api.ts                     # API client with interceptors
│   ├── pages/
│   │   ├── CampaignList.tsx           # Campaign list with filters
│   │   ├── CreateCampaign.tsx         # Multi-step form
│   │   └── AgentMonitor.tsx           # Agent activity dashboard
│   ├── types/
│   │   └── index.ts                   # TypeScript types
│   ├── App.tsx                        # Main app with routing
│   ├── main.tsx                       # Entry point
│   └── index.css                      # Tailwind CSS
├── index.html
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

## 🛠️ Installation

### Prerequisites
- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

### Steps

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```

4. **Open browser:**
   ```
   http://localhost:3000
   ```

## 🔧 Configuration

### API Endpoint
The frontend proxies API requests to the backend. Configure in `vite.config.ts`:

```typescript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
    '/ws': {
      target: 'ws://localhost:8000',
      ws: true,
    },
  },
}
```

### Environment Variables
Create a `.env` file in the frontend directory:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## 📡 Real-Time Updates

### WebSocket Integration

The dashboard uses WebSocket connections for real-time updates:

```typescript
// Automatic connection in components
const { isConnected, lastMessage } = useGeneralWebSocket();

// Campaign-specific updates
const { isConnected } = useCampaignWebSocket(campaignId);
```

### Message Types
- `CAMPAIGN_UPDATE` - Campaign status changes
- `TASK_COMPLETED` - Individual task completion
- `TASK_FAILED` - Task failure
- `PROGRESS_UPDATE` - Progress bar updates
- `AGENT_STATUS` - Agent status changes

## 🎯 Key Components

### CampaignCard
Animated card component with:
- Status badge with pulse animation
- Progress bar with smooth transitions
- Action tags
- Start/Pause button with loading states
- Hover and tap animations

```tsx
<CampaignCard campaign={campaign} />
```

### CreateCampaign
Multi-step wizard with:
- Step 1: Basic info (name, description)
- Step 2: Target URLs (add/remove)
- Step 3: Actions (like, comment, share, follow)
- Step 4: Schedule (priority, timing)

### AgentMonitor
Real-time agent dashboard with:
- Agent status cards
- Activity statistics
- Processing indicators
- Task completion counts
- Last activity timestamps

## 🎬 Animation Examples

### Framer Motion Card Hover
```tsx
<motion.div
  whileHover={{ scale: 1.02, boxShadow: "0 20px 40px rgba(0, 0, 0, 0.12)" }}
  whileTap={{ scale: 0.98 }}
>
  <CampaignCard />
</motion.div>
```

### GSAP Stagger Animation
```tsx
gsap.from('.campaign-card', {
  y: 50,
  opacity: 0,
  stagger: 0.1,
  duration: 0.5,
  ease: 'power2.out'
});
```

### Progress Bar Animation
```tsx
<motion.div
  className="h-full bg-blue-500"
  initial={{ width: 0 }}
  animate={{ width: `${progress}%` }}
  transition={{ duration: 1, ease: 'easeOut' }}
/>
```

## 🔨 Build for Production

```bash
npm run build
```

This creates an optimized build in the `dist` directory.

## 📦 Dependencies

### Core
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server

### Animation
- **Framer Motion** - React animation library
- **GSAP** - Professional-grade animation

### State & Data
- **React Query** - Server state management
- **Zustand** - Client state (if needed)
- **Axios** - HTTP client

### UI & Styling
- **Tailwind CSS** - Utility-first CSS
- **Lucide React** - Icon library
- **clsx** - Conditional class names
- **date-fns** - Date formatting

## 🚦 Development Workflow

1. **Start backend:**
   ```bash
   cd ..
   uvicorn main:app --reload
   ```

2. **Start frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Make changes:**
   - Hot reload is enabled
   - TypeScript errors shown in terminal
   - Browser automatically refreshes

## 🎨 Customization

### Colors
Edit `tailwind.config.js`:
```javascript
colors: {
  linkedin: {
    500: '#0a66c2', // Primary color
    600: '#004182', // Darker shade
  }
}
```

### Animations
Edit animation durations in component files or create reusable variants:
```typescript
const cardVariants = {
  hover: { scale: 1.05, transition: { duration: 0.2 } },
  tap: { scale: 0.95 }
};
```

## 🐛 Troubleshooting

### WebSocket Not Connecting
- Check backend is running
- Verify WebSocket endpoint in backend
- Check browser console for errors

### Animations Not Smooth
- Reduce `stagger` values in GSAP
- Use `will-change: transform` CSS property
- Check browser performance

### API Errors
- Verify backend is running on port 8000
- Check auth token in localStorage
- Review network tab in browser dev tools

## 📝 Future Enhancements

- [ ] Campaign details page with task list
- [ ] Drag-and-drop to reorder target URLs
- [ ] Dark mode support
- [ ] Export campaign results
- [ ] Advanced filtering and sorting
- [ ] Campaign templates
- [ ] Bulk operations
- [ ] Mobile responsive improvements
- [ ] Accessibility enhancements (ARIA labels)
- [ ] Performance monitoring dashboard

## 🤝 Contributing

1. Create a new branch for your feature
2. Make changes and test thoroughly
3. Ensure animations are smooth (60fps)
4. Add TypeScript types for new components
5. Update this README if needed

## 📄 License

Part of the LinkedIn Automation System project.

---

**Built with ❤️ using React, Framer Motion, and GSAP**
