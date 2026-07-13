import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, Dropdown, Avatar } from 'antd';
import {
  DashboardOutlined, VideoCameraOutlined, SendOutlined,
  LinkOutlined, SettingOutlined, LogoutOutlined, MenuFoldOutlined,
  MenuUnfoldOutlined, CrownOutlined, QuestionCircleOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '../stores/authStore';
import FeedbackButton from '../components/FeedbackButton';

const { Header, Sider, Content } = Layout;

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '工作台' },
  { key: '/content', icon: <VideoCameraOutlined />, label: '内容中心' },
  { key: '/publish', icon: <SendOutlined />, label: '发布管理' },
  { key: '/accounts', icon: <LinkOutlined />, label: '账号管理' },
  { key: '/pricing', icon: <CrownOutlined />, label: '套餐升级' },
  { key: '/settings', icon: <SettingOutlined />, label: '设置' },
  { key: '/help', icon: <QuestionCircleOutlined />, label: '帮助中心' },
];

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(window.innerWidth < 768);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        theme="dark"
        breakpoint="lg"
        onBreakpoint={(broken) => setCollapsed(broken)}
      >
        <div style={{
          height: 48, margin: 16, display: 'flex', alignItems: 'center',
          justifyContent: 'center', color: '#fff', fontWeight: 700, fontSize: collapsed ? 14 : 18,
        }}>
          {collapsed ? 'AI' : 'AI获客'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{
          padding: '0 24px', background: '#fff', display: 'flex',
          alignItems: 'center', justifyContent: 'space-between',
          borderBottom: '1px solid #f0f0f0',
        }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          />
          <Dropdown menu={{
            items: [{
              key: 'logout', icon: <LogoutOutlined />, label: '退出登录',
              onClick: () => { logout(); navigate('/login'); },
            }],
          }}>
            <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Avatar size="small">{user?.phone?.slice(-2) || 'U'}</Avatar>
              <span>{user?.company_name || user?.phone || '用户'}</span>
            </div>
          </Dropdown>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: '#fff', borderRadius: 8 }}>
          <Outlet />
        </Content>
        <FeedbackButton />
      </Layout>
    </Layout>
  );
}
