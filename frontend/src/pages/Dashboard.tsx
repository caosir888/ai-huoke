import { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Button, List, Tag, Spin, Progress, Tooltip } from 'antd';
import { VideoCameraOutlined, UploadOutlined, ScissorOutlined, SendOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { listEditTasks } from '../api/content';
import { listPublishTasks } from '../api/publish';
import { getQuotaUsage } from '../api/quota';
import OnboardingGuide from '../components/OnboardingGuide';
import IndustrySelector from '../components/IndustrySelector';

export default function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [editTasks, setEditTasks] = useState<any[]>([]);
  const [pubTasks, setPubTasks] = useState<any[]>([]);
  const [quota, setQuota] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [showGuide, setShowGuide] = useState(!localStorage.getItem('onboarding_done'));
  const [showIndustry, setShowIndustry] = useState(!user?.industry && !localStorage.getItem('industry_skipped'));

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [editRes, pubRes, quotaRes] = await Promise.all([
          listEditTasks(), listPublishTasks(), getQuotaUsage(),
        ]);
        setEditTasks(editRes.data.slice(0, 5));
        setPubTasks(pubRes.data.slice(0, 5));
        setQuota(quotaRes);
      } catch { /* backend not available yet */ }
      setLoading(false);
    };
    fetchData();
  }, []);

  const quickActions = [
    { title: '生成文案', icon: <VideoCameraOutlined />, path: '/content?tab=copywriting', color: '#1677ff' },
    { title: '上传素材', icon: <UploadOutlined />, path: '/content?tab=materials', color: '#52c41a' },
    { title: '创建混剪', icon: <ScissorOutlined />, path: '/content?tab=edit', color: '#fa8c16' },
    { title: '发布视频', icon: <SendOutlined />, path: '/publish', color: '#722ed1' },
  ];

  const handleOneClick = () => {
    // Navigate to content center to start the full flow
    navigate('/content');
    // Show onboarding guide if user hasn't completed it
    if (!localStorage.getItem('onboarding_done')) {
      setShowGuide(true);
    }
  };

  const statusColors: Record<string, string> = {
    pending: 'default', processing: 'processing', done: 'success', failed: 'error',
    published: 'success', publishing: 'processing',
  };

  return (
    <Spin spinning={loading}>
      <h2 style={{ marginBottom: 24 }}>早上好，{user?.company_name || '老板'}！</h2>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="今日发布" value={pubTasks.filter(t => t.status === 'published').length} suffix="条" /></Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="总播放量" value={pubTasks.reduce((sum: number, t: any) => sum + (t.metrics?.plays || 0), 0)} /></Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="总互动量" value={pubTasks.reduce((sum: number, t: any) => sum + ((t.metrics?.likes || 0) + (t.metrics?.comments || 0)), 0)} /></Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="待处理任务" value={editTasks.filter(t => t.status === 'pending' || t.status === 'processing').length} /></Card>
        </Col>
      </Row>

      {quota && (
        <Card title={<span>用量概览 <Tag>{quota.plan_name}</Tag></span>}
          style={{ marginTop: 24 }}
          extra={<Button size="small" type="link" onClick={() => navigate('/settings')}>升级套餐</Button>}
        >
          <Row gutter={24}>
            <Col span={6}>
              <Tooltip title={`今日已用 ${quota.daily_edit.used} / ${quota.daily_edit.limit}`}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ marginBottom: 4, color: '#666', fontSize: 13 }}>今日剪辑</div>
                  <Progress type="circle" size={60} percent={Math.min(100, Math.round(quota.daily_edit.used / Math.max(1, quota.daily_edit.limit) * 100))} width={6} />
                  <div style={{ marginTop: 4, fontSize: 12, color: '#999' }}>{quota.daily_edit.used}/{quota.daily_edit.limit}</div>
                </div>
              </Tooltip>
            </Col>
            <Col span={6}>
              <Tooltip title={`本月已用 ${quota.monthly_edit.used} / ${quota.monthly_edit.limit}`}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ marginBottom: 4, color: '#666', fontSize: 13 }}>本月剪辑</div>
                  <Progress type="circle" size={60} percent={Math.min(100, Math.round(quota.monthly_edit.used / Math.max(1, quota.monthly_edit.limit) * 100))} width={6} />
                  <div style={{ marginTop: 4, fontSize: 12, color: '#999' }}>{quota.monthly_edit.used}/{quota.monthly_edit.limit}</div>
                </div>
              </Tooltip>
            </Col>
            <Col span={6}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ marginBottom: 4, color: '#666', fontSize: 13 }}>绑定账号</div>
                <Progress type="circle" size={60} percent={Math.min(100, Math.round(quota.accounts.used / Math.max(1, quota.accounts.limit) * 100))} width={6} />
                <div style={{ marginTop: 4, fontSize: 12, color: '#999' }}>{quota.accounts.used}/{quota.accounts.limit}</div>
              </div>
            </Col>
            <Col span={6}>
              <Tooltip title={`存储 ${quota.storage.used_gb}GB / ${quota.storage.limit_gb}GB`}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ marginBottom: 4, color: '#666', fontSize: 13 }}>存储空间</div>
                  <Progress type="circle" size={60} percent={Math.min(100, Math.round(quota.storage.used / Math.max(1, quota.storage.limit) * 100))} width={6} />
                  <div style={{ marginTop: 4, fontSize: 12, color: '#999' }}>{quota.storage.used_gb}/{quota.storage.limit_gb}GB</div>
                </div>
              </Tooltip>
            </Col>
          </Row>
        </Card>
      )}

      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={12}>
          <Card title="快捷操作">
            <Button
              type="primary"
              size="large"
              icon={<ThunderboltOutlined />}
              block
              style={{ marginBottom: 16, height: 48, fontSize: 16 }}
              onClick={handleOneClick}
            >
              一键生成视频 — 快速上手
            </Button>
            <Row gutter={[16, 16]}>
              {quickActions.map((action) => (
                <Col span={12} key={action.title}>
                  <Button block size="large" icon={action.icon}
                    style={{ height: 80, borderColor: action.color, color: action.color }}
                    onClick={() => navigate(action.path)}>
                    {action.title}
                  </Button>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="最近任务">
            <List
              dataSource={[...editTasks, ...pubTasks].sort((a, b) =>
                new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
              ).slice(0, 8)}
              locale={{ emptyText: '暂无任务，快去创建第一条视频吧' }}
              renderItem={(item: any) => (
                <List.Item>
                  <Tag color={statusColors[item.status]}>{item.status}</Tag>
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.title || `混剪任务 ${item.id?.slice(0, 8)}`}
                  </span>
                  <span style={{ color: '#999', fontSize: 12 }}>
                    {item.created_at ? new Date(item.created_at).toLocaleString() : ''}
                  </span>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
      <OnboardingGuide visible={showGuide} onClose={() => setShowGuide(false)} />
      <IndustrySelector open={showIndustry} onClose={() => {
        localStorage.setItem('industry_skipped', 'true');
        setShowIndustry(false);
      }} />
    </Spin>
  );
}
