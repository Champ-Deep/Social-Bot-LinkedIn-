import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AnimatePresence, motion } from 'framer-motion';
import { CampaignList } from './pages/CampaignList';
import { CreateCampaign } from './pages/CreateCampaign';
import { AgentMonitor } from './pages/AgentMonitor';
import { Navigation } from './components/Navigation';

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 3000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-50">
          <Navigation />
          <AnimatedRoutes />
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

function AnimatedRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<Navigate to="/campaigns" replace />} />
        <Route
          path="/campaigns"
          element={
            <PageWrapper>
              <CampaignList />
            </PageWrapper>
          }
        />
        <Route
          path="/campaigns/new"
          element={
            <PageWrapper>
              <CreateCampaign />
            </PageWrapper>
          }
        />
        <Route
          path="/agents"
          element={
            <PageWrapper>
              <AgentMonitor />
            </PageWrapper>
          }
        />
        {/* Catch-all redirect */}
        <Route path="*" element={<Navigate to="/campaigns" replace />} />
      </Routes>
    </AnimatePresence>
  );
}

function PageWrapper({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
    >
      {children}
    </motion.div>
  );
}

export default App;
