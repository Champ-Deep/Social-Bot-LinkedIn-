# Frontend Setup Guide
## Complete Installation and Configuration

---

## 🎯 Overview

This guide will walk you through setting up the LinkedIn Automation Dashboard frontend, connecting it to your FastAPI backend, and getting real-time updates working.

---

## 📋 Prerequisites

Before starting, ensure you have:

- ✅ **Node.js 18+** installed ([Download](https://nodejs.org/))
- ✅ **npm 9+** (comes with Node.js)
- ✅ **Backend running** on `http://localhost:8000`
- ✅ **Git** installed (for version control)

Check your versions:
```bash
node --version  # Should be v18.0.0 or higher
npm --version   # Should be 9.0.0 or higher
```

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Navigate to Frontend Directory
```bash
cd /home/user/Social-Bot-LinkedIn-/frontend
```

### Step 2: Install Dependencies
```bash
npm install
```

This will install all required packages (React, Framer Motion, GSAP, etc.)

### Step 3: Start Development Server
```bash
npm run dev
```

You should see:
```
  VITE v5.0.8  ready in 500 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
  ➜  press h to show help
```

### Step 4: Open Browser
Navigate to: **http://localhost:3000**

You should see the campaign list page!

---

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/           # Reusable components
│   │   ├── campaigns/
│   │   │   └── CampaignCard.tsx
│   │   └── Navigation.tsx
│   ├── pages/               # Page components
│   │   ├── CampaignList.tsx
│   │   ├── CreateCampaign.tsx
│   │   └── AgentMonitor.tsx
│   ├── hooks/               # Custom React hooks
│   │   └── useWebSocket.ts
│   ├── lib/                 # Utilities
│   │   └── api.ts
│   ├── types/               # TypeScript types
│   │   └── index.ts
│   ├── App.tsx              # Main app component
│   ├── main.tsx             # Entry point
│   └── index.css            # Global styles
├── public/                  # Static assets
├── index.html               # HTML template
├── package.json             # Dependencies
├── vite.config.ts           # Vite configuration
├── tailwind.config.js       # Tailwind CSS config
└── tsconfig.json            # TypeScript config
```

---

## 🔧 Configuration

### 1. API Endpoint Configuration

The frontend is pre-configured to proxy API requests to your backend.

**File: `vite.config.ts`**
```typescript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',  // Your backend URL
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
    '/ws': {
      target: 'ws://localhost:8000',    // WebSocket URL
      ws: true,
    },
  },
}
```

**If your backend runs on a different port:**
1. Edit `vite.config.ts`
2. Change `http://localhost:8000` to your backend URL
3. Restart the dev server (`Ctrl+C`, then `npm run dev`)

### 2. Environment Variables (Optional)

Create a `.env` file in the `frontend/` directory:

```env
# API Configuration
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000

# Optional: Enable debugging
VITE_DEBUG=true
```

---

## 🎨 Features Overview

### 1. Campaign List Page
**URL:** http://localhost:3000/campaigns

**Features:**
- ✅ Animated campaign cards with Framer Motion
- ✅ Real-time progress bars
- ✅ Filter by status (All, Running, Draft, etc.)
- ✅ Search campaigns by name
- ✅ Start/Pause campaigns with loading states
- ✅ Live WebSocket connection indicator
- ✅ GSAP stagger animations on page load

**Animations:**
- Cards slide in from bottom with stagger effect
- Hover: Card scales up with shadow
- Tap: Card scales down
- Progress bars animate smoothly
- Status badges pulse when campaign is running

### 2. Create Campaign Page
**URL:** http://localhost:3000/campaigns/new

**Features:**
- ✅ Multi-step wizard (4 steps)
- ✅ Animated progress indicator
- ✅ Form validation at each step
- ✅ Add/remove target URLs
- ✅ Select automation actions
- ✅ Set priority and schedule
- ✅ Campaign summary preview

**Animations:**
- Steps slide horizontally (forward/backward)
- Progress bar fills smoothly
- Checkmarks animate when step is completed
- Action cards scale on selection
- Submit button morphs to loading spinner

### 3. Agent Activity Monitor
**URL:** http://localhost:3000/agents

**Features:**
- ✅ Real-time agent status
- ✅ Activity statistics
- ✅ Agent-specific icons and colors
- ✅ Task completion counts
- ✅ Last activity timestamps
- ✅ Processing indicators

**Animations:**
- Agent cards slide in with stagger
- Processing agents have pulsing box shadows
- Status dots pulse for active agents
- Progress bars for ongoing tasks
- Stats animate with spring physics

---

## 🌐 Connecting to Backend

### Backend API Endpoints Used

The frontend expects these endpoints to be available:

#### Campaigns
- `GET /campaigns` - List all campaigns
- `GET /campaigns/:id` - Get campaign details
- `POST /campaigns` - Create new campaign
- `PATCH /campaigns/:id` - Update campaign
- `DELETE /campaigns/:id` - Delete campaign
- `POST /campaigns/:id/start` - Start campaign
- `POST /campaigns/:id/pause` - Pause campaign
- `GET /campaigns/:id/status` - Get progress
- `GET /campaigns/:id/tasks` - Get tasks

#### WebSocket
- `WS /ws/campaigns/:id` - Campaign-specific updates
- `WS /ws/updates` - General system updates

### Testing Backend Connection

1. **Start your backend:**
   ```bash
   cd /home/user/Social-Bot-LinkedIn-
   uvicorn main:app --reload --port 8000
   ```

2. **Verify API is responding:**
   ```bash
   curl http://localhost:8000/campaigns
   ```

   You should see JSON response with campaigns.

3. **Check WebSocket (optional):**
   Use a WebSocket testing tool like [WebSocket King](https://websocketking.com/)
   - Connect to: `ws://localhost:8000/ws/updates`
   - You should see connection established

---

## 📡 Real-Time Updates

### How WebSocket Integration Works

1. **Automatic Connection:**
   When you open the dashboard, it automatically connects to the WebSocket endpoint.

2. **Connection Indicator:**
   Look for the "Live" badge with a pulsing green dot in the header.

3. **Automatic Updates:**
   - Campaign status changes → Updates campaign card
   - Task completion → Updates progress bar
   - Agent status → Updates agent monitor

4. **Reconnection Logic:**
   If connection drops, it automatically reconnects:
   - Attempt 1: After 3 seconds
   - Attempt 2: After 6 seconds
   - Attempt 3: After 9 seconds
   - Up to 5 attempts total

### Testing Real-Time Updates

1. **Open the dashboard** in your browser
2. **Start a campaign** by clicking "Start Campaign"
3. **Watch the progress bar** update in real-time
4. **Open Agent Monitor** to see agents processing tasks

---

## 🎬 Animation Details

### Framer Motion (Component-Level)

Used for:
- Card hover/tap effects
- Button interactions
- Page transitions
- Layout animations

Example from CampaignCard:
```tsx
<motion.div
  whileHover={{ scale: 1.02 }}
  whileTap={{ scale: 0.98 }}
  transition={{ type: "spring", stiffness: 300 }}
>
  <CampaignCard />
</motion.div>
```

### GSAP (Timeline Animations)

Used for:
- Page entry animations
- Staggered list reveals
- Pulsing effects
- Complex sequences

Example from CampaignList:
```tsx
gsap.from('.campaign-card', {
  y: 50,
  opacity: 0,
  stagger: 0.1,
  duration: 0.5,
  ease: 'power2.out'
});
```

---

## 🐛 Troubleshooting

### Issue: "Cannot connect to backend"

**Solution:**
1. Verify backend is running: `curl http://localhost:8000/campaigns`
2. Check `vite.config.ts` has correct backend URL
3. Restart dev server: `Ctrl+C`, then `npm run dev`

### Issue: "WebSocket not connecting"

**Solution:**
1. Check browser console for errors (F12 → Console tab)
2. Verify WebSocket endpoint exists in backend
3. Check for CORS issues in backend logs

### Issue: "Animations are laggy"

**Solution:**
1. Close other browser tabs
2. Check Chrome/Firefox performance tab
3. Reduce `stagger` values in animation code
4. Use `will-change: transform` CSS property

### Issue: "npm install fails"

**Solution:**
1. Delete `node_modules` and `package-lock.json`
2. Run `npm cache clean --force`
3. Run `npm install` again

### Issue: "Port 3000 already in use"

**Solution:**
1. Change port in `vite.config.ts`:
   ```typescript
   server: { port: 3001 }
   ```
2. Or kill process on port 3000:
   ```bash
   lsof -ti:3000 | xargs kill
   ```

---

## 🚦 Development Workflow

### Typical Development Session

1. **Start backend:**
   ```bash
   cd /home/user/Social-Bot-LinkedIn-
   uvicorn main:app --reload
   ```

2. **Start frontend (new terminal):**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Make changes:**
   - Edit files in `src/`
   - Save changes
   - Browser auto-refreshes
   - TypeScript errors show in terminal

4. **Test in browser:**
   - Open http://localhost:3000
   - Test interactions
   - Check console for errors (F12)

### Hot Module Replacement (HMR)

Changes you make are instantly reflected without full page reload:
- ✅ Component changes
- ✅ Style changes
- ✅ Type changes
- ⚠️ Config changes require restart

---

## 📦 Building for Production

### Step 1: Build
```bash
npm run build
```

This creates an optimized build in `dist/` directory.

### Step 2: Preview Build
```bash
npm run preview
```

Opens the production build at http://localhost:4173

### Step 3: Deploy

**Option A: Static Hosting (Vercel, Netlify)**
```bash
# Deploy dist/ folder
vercel --prod
# or
netlify deploy --prod --dir=dist
```

**Option B: Docker**
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
CMD ["npm", "run", "preview"]
```

---

## 🔐 Authentication (TODO)

Currently, authentication is stubbed. To implement:

1. **Add login page:**
   ```tsx
   // src/pages/Login.tsx
   export function Login() {
     // Supabase auth logic
   }
   ```

2. **Update API client:**
   ```typescript
   // src/lib/api.ts
   const token = localStorage.getItem('auth_token');
   config.headers.Authorization = `Bearer ${token}`;
   ```

3. **Add protected routes:**
   ```tsx
   <Route path="/campaigns" element={
     <ProtectedRoute>
       <CampaignList />
     </ProtectedRoute>
   } />
   ```

---

## 📊 Performance Tips

### Optimization Checklist

- ✅ Use `React.memo()` for expensive components
- ✅ Lazy load routes with `React.lazy()`
- ✅ Use `useCallback` for event handlers
- ✅ Use `useMemo` for computed values
- ✅ Enable React Query caching
- ✅ Optimize images (use WebP)
- ✅ Code splitting with dynamic imports

### Animation Performance

- ✅ Use `transform` and `opacity` (GPU accelerated)
- ✅ Avoid animating `width`, `height`, `top`, `left`
- ✅ Use `will-change: transform` sparingly
- ✅ Reduce stagger values for large lists
- ✅ Use `layoutId` for shared element transitions

---

## 🎓 Learning Resources

### Framer Motion
- [Official Docs](https://www.framer.com/motion/)
- [Examples](https://www.framer.com/motion/examples/)
- [API Reference](https://www.framer.com/motion/component/)

### GSAP
- [Getting Started](https://greensock.com/get-started/)
- [Cheat Sheet](https://greensock.com/cheatsheet/)
- [ScrollTrigger](https://greensock.com/scrolltrigger/)

### React Query
- [Overview](https://tanstack.com/query/latest)
- [Quick Start](https://tanstack.com/query/latest/docs/react/quick-start)

---

## 🤝 Contributing

### Making Changes

1. **Create a branch:**
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make changes and test:**
   - Add new components
   - Write TypeScript types
   - Test animations (should be 60fps)

3. **Commit and push:**
   ```bash
   git add .
   git commit -m "Add my new feature"
   git push origin feature/my-new-feature
   ```

### Code Style

- ✅ Use TypeScript for all new files
- ✅ Follow existing naming conventions
- ✅ Add JSDoc comments for complex functions
- ✅ Use Tailwind classes instead of custom CSS
- ✅ Keep components under 300 lines

---

## 📝 Next Steps

Now that your frontend is running, you can:

1. **Create your first campaign:**
   - Click "New Campaign"
   - Fill out the 4-step form
   - Watch it appear in the list

2. **Monitor agents:**
   - Navigate to "Agents" tab
   - Watch real-time status updates

3. **Customize the UI:**
   - Edit colors in `tailwind.config.js`
   - Modify animations in component files
   - Add new features

4. **Connect real backend:**
   - Ensure all API endpoints are implemented
   - Test WebSocket updates
   - Verify authentication

---

## 🆘 Getting Help

If you encounter issues:

1. **Check this guide** for common solutions
2. **Review browser console** (F12 → Console)
3. **Check backend logs** for API errors
4. **Test API manually** with `curl` or Postman

---

## 🎉 You're All Set!

Your LinkedIn Automation Dashboard is now running with:
- ✅ Animated campaign cards
- ✅ Multi-step campaign creation
- ✅ Real-time WebSocket updates
- ✅ Agent activity monitoring
- ✅ GSAP + Framer Motion animations

**Happy automating! 🚀**
