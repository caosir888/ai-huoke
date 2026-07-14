import { useState, useEffect, useRef } from 'react';
import { Card, Table, Tag, Button, Modal, Select, Input, DatePicker, Space, message, Statistic, Row, Col, Progress } from 'antd';
import { SendOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { listPublishTasks, createPublishTask } from '../api/publish';
import { listAccounts } from '../api/platform';
import { handleApiError, showSuccess } from '../utils/errorHandler';
import VideoDataPanel from '../components/VideoDataPanel';

const statusColors: Record<string, string> = {
  pending: 'default', publishing: 'processing', published: 'success', failed: 'error', queued: 'warning',
};

const statusText: Record<string, string> = {
  pending: '待发布', publishing: '发布中', published: '已发布', failed: '失败', queued: 'RPA排队',
};

export default function PublishManagement() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);

  // Create form
  const [videoUrl, setVideoUrl] = useState('');
  const [selectedAccount, setSelectedAccount] = useState('');
  const [title, setTitle] = useState('');
  const [scheduleType, setScheduleType] = useState<'now' | 'timed'>('now');
  const [scheduleTime, setScheduleTime] = useState<string>('');
  const [submitting, setSubmitting] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [taskRes, accRes] = await Promise.all([listPublishTasks(), listAccounts()]);
      setTasks(taskRes.data);
      setAccounts(accRes.data);
    } catch (err) { handleApiError(err, '加载发布数据失败'); }
    setLoading(false);
  };

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => { fetchData(); }, []);

  // Auto-poll when any task is publishing
  useEffect(() => {
    const hasPublishing = tasks.some(t => t.status === 'publishing');
    if (hasPublishing && !pollingRef.current) {
      pollingRef.current = setInterval(fetchData, 2000);
    } else if (!hasPublishing && pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    return () => {
      if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
    };
  }, [tasks]);

  const handlePublish = async () => {
    if (!videoUrl || !selectedAccount || !title) {
      message.warning('请填写完整信息');
      return;
    }
    setSubmitting(true);
    try {
      await createPublishTask({
        video_url: videoUrl,
        platform_account_id: selectedAccount,
        title,
        schedule_type: scheduleType,
        schedule_time: scheduleType === 'timed' ? scheduleTime : undefined,
      });
      showSuccess(scheduleType === 'now' ? '已发布' : '已排期');
      setCreateOpen(false);
      setVideoUrl(''); setTitle(''); setSelectedAccount('');
      fetchData();
    } catch (err) { handleApiError(err, '发布失败'); }
    setSubmitting(false);
  };

  const columns: ColumnsType<any> = [
    { title: '视频', dataIndex: 'video_url', key: 'video', ellipsis: true, width: 200,
      render: (url: string) => <a href={url} target="_blank">{url.split('/').pop()}</a> },
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (s: string) => <Tag color={statusColors[s]}>{statusText[s]}</Tag> },
    { title: '进度', key: 'progress', width: 120,
      render: (_, r) => r.status === 'publishing' ? <Progress percent={r.progress || 0} size="small" style={{ width: 100 }} /> : (r.status === 'published' ? <span style={{ color: '#52c41a' }}>100%</span> : '-') },
    { title: '平台', dataIndex: 'platform_account_id', key: 'platform', width: 100 },
    { title: '播放', key: 'plays', width: 80,
      render: (_, r) => r.metrics?.plays || '-' },
    { title: '点赞', key: 'likes', width: 80,
      render: (_, r) => r.metrics?.likes || '-' },
    { title: '评论', key: 'comments', width: 80,
      render: (_, r) => r.metrics?.comments || '-' },
    { title: '时间', dataIndex: 'created_at', key: 'time', width: 160,
      render: (d: string) => dayjs(d).format('MM-DD HH:mm') },
  ];

  const activeAccounts = accounts.filter(a => a.auth_status === 'active');

  return (
    <div>
      <h2>发布管理</h2>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}><Card><Statistic title="总发布" value={tasks.length} /></Card></Col>
        <Col span={6}><Card><Statistic title="已发布" value={tasks.filter(t => t.status === 'published').length} valueStyle={{ color: '#52c41a' }} /></Card></Col>
        <Col span={6}><Card><Statistic title="总播放" value={tasks.reduce((s, t) => s + (t.metrics?.plays || 0), 0)} /></Card></Col>
        <Col span={6}><Card><Statistic title="待处理" value={tasks.filter(t => t.status === 'pending').length} valueStyle={{ color: '#faad14' }} /></Card></Col>
      </Row>

      <Card title="发布任务" extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          <Button type="primary" icon={<SendOutlined />} onClick={() => setCreateOpen(true)}
            disabled={activeAccounts.length === 0}>
            发布视频
          </Button>
        </Space>
      }>
        {activeAccounts.length === 0 && (
          <p style={{ color: '#faad14', marginBottom: 16 }}>
            尚未绑定平台账号，请先在「账号管理」中绑定抖音/快手/小红书账号
          </p>
        )}
        <Table columns={columns} dataSource={tasks} rowKey="id" loading={loading} size="small"
          locale={{ emptyText: '还没有发布任务' }} />
      </Card>

      <Modal title="发布视频" open={createOpen} onCancel={() => setCreateOpen(false)}
        onOk={handlePublish} confirmLoading={submitting} okText="发布" width={500}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <label>视频URL</label>
          <Input placeholder="选择已混剪的视频URL" value={videoUrl}
            onChange={e => setVideoUrl(e.target.value)} />
          <label>发布账号</label>
          <Select placeholder="选择平台账号" value={selectedAccount || undefined}
            onChange={setSelectedAccount} style={{ width: '100%' }}
            options={activeAccounts.map(a => ({
              label: `${a.platform.toUpperCase()} - ${a.account_name}`,
              value: a.id,
            }))} />
          <label>标题</label>
          <Input.TextArea placeholder="输入视频标题和描述" value={title}
            onChange={e => setTitle(e.target.value)} rows={3} maxLength={500} />
          <label>发布方式</label>
          <Select value={scheduleType} onChange={setScheduleType}
            options={[
              { label: '立即发布', value: 'now' },
              { label: '定时发布', value: 'timed' },
            ]} />
          {scheduleType === 'timed' && (
            <DatePicker showTime value={scheduleTime ? dayjs(scheduleTime) : null}
              onChange={(d) => setScheduleTime(d?.toISOString() || '')}
              style={{ width: '100%' }} placeholder="选择发布时间" />
          )}
        </div>
      </Modal>

      <VideoDataPanel tasks={tasks} />
    </div>
  );
}
