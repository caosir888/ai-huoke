import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { useEffect } from 'react';
import MainLayout from './layouts/MainLayout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import ContentCenter from './pages/ContentCenter';
import PublishManagement from './pages/PublishManagement';
import Analytics from './pages/Analytics';
import AccountManagement from './pages/AccountManagement';
import Settings from './pages/Settings';
import Pricing from './pages/Pricing';
import Help from './pages/Help';
import AdminUsers from './pages/AdminUsers';
import ErrorBoundary from './components/ErrorBoundary';
import { useAuthStore } from './stores/authStore';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('token');
  if (!token) return <Navigate to="/login" />;
  return <>{children}</>;
}

export default function App() {
  const { fetchUser, loading } = useAuthStore();

  useEffect(() => {
    fetchUser();
  }, []);

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      加载中...
    </div>
  );

  return (
    <ConfigProvider locale={zhCN}>
      <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="content" element={<ContentCenter />} />
            <Route path="publish" element={<PublishManagement />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="accounts" element={<AccountManagement />} />
            <Route path="settings" element={<Settings />} />
            <Route path="pricing" element={<Pricing />} />
            <Route path="help" element={<Help />} />
            <Route path="admin" element={<AdminUsers />} />
          </Route>
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </BrowserRouter>
      </ErrorBoundary>
    </ConfigProvider>
  );
}
