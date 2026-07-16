import { useState, useEffect, useRef, useCallback } from 'react';
import { Card, Table, Tag, Button, Modal, Select, Input, DatePicker, Space, message, Statistic, Row, Col, Progress, Popconfirm } from 'antd';
import { SendOutlined, ReloadOutlined, ClockCircleOutlined, EditOutlined, CloseOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { listPublishTasks, createPublishTask, reschedule, cancelPublishTask } from '../api/publish';
import { listEditTasks } from '../api/content';
import { listAccounts } from '../api/platform';
import { handleApiError, showSuccess } from '../utils/errorHandler';
import VideoDataPanel from '../components/VideoDataPanel';

const statusColors: Record<string, string> = {
  pending: 'default', publishing: 'processing', published: 'success', failed: 'error', cancelled: '#999', queued: 'warning',
};

const statusText: Record<string, string> = {
  pending: '待发布', publishing: '发布中', published: '已发布', failed: '失败', cancelled: '已取消', queued: 'RPA排队',
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
  const [videoOptions, setVideoOptions] = useState<{ label: string; value: string; title: string }[]>([]);

  const loadVideoOptions = async () => {
    try {
      const { data } = await listEditTasks();
      const opts: { label: string; value: string; title: string; thumb?: string }[] = [];
      for (const t of data) {
        if (t.status !== 'done' || !t.output_urls?.length) continue;
        for (let i = 0; i < t.output_urls.length; i++) {
          const url = t.output_urls[i];
          const resolved = url.startsWith('http') ? url : 'http://localhost:8000' + url;
          const thumbs = t.thumbnail_urls || [];
          const thumbUrl = thumbs[i]
            ? (thumbs[i].startsWith('http') ? thumbs[i] : 'http://localhost:8000' + thumbs[i])
            : undefined;
          const label = `混剪 #${t.id.slice(0, 8)} - 视频${i + 1} (${t.material_ids?.length || 0}段素材)`;
          opts.push({ label, value: resolved, title: `混剪视频 ${t.id.slice(0, 8)}`, thumb: thumbUrl });
        }
      }
      setVideoOptions(opts);
    } catch { /* ignore */ }
  };

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [taskRes, accRes] = await Promise.all([listPublishTasks(), listAccounts()]);
      setTasks(taskRes.data);
      setAccounts(accRes.data);
    } catch (err) { handleApiError(err, '加载发布数据失败'); }
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Auto-poll when any task is publishing
  useEffect(() => {
    const hasActive = tasks.some(t => t.status === 'publishing');

    if (hasActive && !pollingRef.current) {
      pollingRef.current = setInterval(fetchData, 2000);
    } else if (!hasActive && pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }

    return () => {
      if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
    };
  }, [tasks, fetchData]);

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

  const handleReschedule = async (taskId: string) => {
    // Use a simple prompt for the new time
    const newTime = prompt('输入新的发布时间（ISO格式，如 2026-07-15T14:00:00）');
    if (!newTime) return;
    try {
      await reschedule(taskId, newTime);
      showSuccess('已重新排期');
      fetchData();
    } catch (err) { handleApiError(err, '重新排期失败'); }
  };

  const handleCancel = async (taskId: string) => {
    try {
      await cancelPublishTask(taskId);
      showSuccess('已取消');
      fetchData();
    } catch (err) { handleApiError(err, '取消失败'); }
  };

  const countdownText = (scheduleTime: string) => {
    const diff = dayjs(scheduleTime).diff(dayjs(), 'second');
    if (diff <= 0) return <Tag color="processing">即将执行</Tag>;
    const h = Math.floor(diff / 3600);
    const m = Math.floor((diff % 3600) / 60);
    const s = diff % 60;
    if (h > 0) return <span style={{ color: '#1677ff' }}>{h}h {m}m 后</span>;
    if (m > 0) return <span style={{ color: '#fa8c16' }}>{m}m {s}s 后</span>;
    return <span style={{ color: '#ff4d4f' }}>{s}s 后</span>;
  };

  const columns: ColumnsType<any> = [
    { title: '视频', dataIndex: 'video_url', key: 'video', ellipsis: true, width: 180,
      render: (url: string) => <a href={url} target="_blank">{url.split('/').pop()}</a> },
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90,
      render: (s: string) => <Tag color={statusColors[s]}>{statusText[s]}</Tag> },
    { title: '进度', key: 'progress', width: 110,
      render: (_, r) => r.status === 'publishing' ? <Progress percent={r.progress || 0} size="small" style={{ width: 100 }} /> : (r.status === 'published' ? <span style={{ color: '#52c41a' }}>100%</span> : '-') },
    { title: '排期', key: 'schedule', width: 140,
      render: (_, r) => {
        if (r.schedule_type !== 'timed' || !r.schedule_time) return <span style={{ color: '#999' }}>即时</span>;
        return (
          <div>
            <div style={{ fontSize: 12 }}>{dayjs(r.schedule_time).format('MM-DD HH:mm')}</div>
            {r.status === 'pending' && <div style={{ fontSize: 12 }}>{countdownText(r.schedule_time)}</div>}
          </div>
        );
      }
    },
    { title: '平台', dataIndex: 'platform_account_id', key: 'platform', width: 80 },
    { title: '播放', key: 'plays', width: 70,
      render: (_, r) => r.metrics?.plays || '-' },
    { title: '点赞', key: 'likes', width: 70,
      render: (_, r) => r.metrics?.likes || '-' },
    { title: '时间', dataIndex: 'created_at', key: 'time', width: 110,
      render: (d: string) => dayjs(d).format('MM-DD HH:mm') },
    { title: '操作', key: 'action', width: 120, render: (_, r) => {
      if (r.status !== 'pending' || r.schedule_type !== 'timed') return null;
      return (
        <Space size={0}>
          <Button size="small" type="link" icon={<EditOutlined />}
            onClick={() => handleReschedule(r.id)}>改期</Button>
          <Popconfirm title="确定取消此排期？" onConfirm={() => handleCancel(r.id)}>
            <Button size="small" type="link" danger icon={<CloseOutlined />}>取消</Button>
          </Popconfirm>
        </Space>
      );
    }},
  ];

  const activeAccounts = accounts.filter(a => a.auth_status === 'active');

  return (
    <div>
      <h2>发布管理</h2>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}><Card><Statistic title="总发布" value={tasks.length} /></Card></Col>
        <Col span={6}><Card><Statistic title="已发布" value={tasks.filter(t => t.status === 'published').length} valueStyle={{ color: '#52c41a' }} /></Card></Col>
        <Col span={6}><Card><Statistic title="总播放" value={tasks.reduce((s, t) => s + (t.metrics?.plays || 0), 0)} /></Card></Col>
        <Col span={6}><Card><Statistic title="定时排期" value={tasks.filter(t => t.schedule_type === 'timed' && t.status === 'pending').length} valueStyle={{ color: '#1677ff' }}
          prefix={<ClockCircleOutlined />} /></Card></Col>
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
        onOk={handlePublish} confirmLoading={submitting} okText="发布" width={500}
        afterOpenChange={(vis) => { if (vis) loadVideoOptions(); }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <label>选择视频</label>
          <Select
            showSearch
            placeholder="选择已完成的混剪视频"
            value={videoUrl || undefined}
            onChange={(val, opt: any) => {
              setVideoUrl(val);
              if (!title && opt?.title) setTitle(opt.title);
            }}
            style={{ width: '100%' }}
            options={videoOptions}
            notFoundContent={videoOptions.length === 0 ? '暂无已完成的混剪视频，请先去混剪任务中生成' : '未找到匹配视频'}
            filterOption={(input, option) => (option?.label ?? '').toLowerCase().includes(input.toLowerCase())}
            optionRender={(option) => (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {option.data.thumb
                  ? <img src={option.data.thumb} style={{ width: 64, height: 36, objectFit: 'cover', borderRadius: 3 }} alt="" />
                  : <span style={{ width: 64, height: 36, background: '#f0f0f0', borderRadius: 3, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, color: '#999' }}>无封面</span>}
                <span>{option.label}</span>
              </div>
            )}
          />
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
              onChange={(d) => setScheduleTime(d ? d.toISOString() : '')}
              style={{ width: '100%' }} placeholder="选择发布时间"
              disabledDate={(d) => d && d.isBefore(dayjs(), 'minute')} />
          )}
        </div>
      </Modal>

      <VideoDataPanel tasks={tasks} />
    </div>
  );
}
