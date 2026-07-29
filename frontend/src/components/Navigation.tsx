import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { LayoutDashboard, Activity, Settings } from 'lucide-react';
import { clsx } from 'clsx';

const navItems = [
  {
    path: '/campaigns',
    label: 'Campaigns',
    icon: LayoutDashboard,
  },
  {
    path: '/agents',
    label: 'Agents',
    icon: Activity,
  },
];

export function Navigation() {
  const location = useLocation();

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <motion.div
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="text-2xl font-bold bg-gradient-to-r from-linkedin-500 to-linkedin-600 bg-clip-text text-transparent"
            >
              LinkedIn Automation
            </motion.div>
          </Link>

          {/* Navigation Links */}
          <div className="flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname.startsWith(item.path);

              return (
                <Link key={item.path} to={item.path}>
                  <motion.div
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className={clsx(
                      'flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors',
                      isActive
                        ? 'bg-linkedin-50 text-linkedin-600'
                        : 'text-gray-600 hover:bg-gray-100'
                    )}
                  >
                    <Icon size={20} />
                    <span>{item.label}</span>
                    {isActive && (
                      <motion.div
                        layoutId="activeTab"
                        className="absolute bottom-0 left-0 right-0 h-0.5 bg-linkedin-500"
                        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                      />
                    )}
                  </motion.div>
                </Link>
              );
            })}

            {/* Settings */}
            <motion.button
              whileHover={{ scale: 1.05, rotate: 90 }}
              whileTap={{ scale: 0.95 }}
              className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg ml-4"
            >
              <Settings size={20} />
            </motion.button>
          </div>
        </div>
      </div>
    </nav>
  );
}
