import { useState, useEffect, useCallback } from 'react';
import { Card, Table, Tag, Progress, Button } from 'antd';
import { EyeOutlined, DownloadOutlined, PlusOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { listEditTasks } from '../api/content';
import { handleApiError } from '../utils/errorHandler';
import EditTaskWizard from './EditTaskWizard';
import VideoPreview from './VideoPreview';

interface EditTask {
  id: string;
  material_ids: string[];
  status: string;
  progress: number;
  output_urls: string[];
  error_message: string | null;
  created_at: string;
}

const statusMap: Record<string, { color: string; text: string }> = {
  pending: { color: 'default', text: '排队中' },
  processing: { color: 'processing', text: '处理中' },
  done: { color: 'success', text: '已完成' },
  failed: { color: 'error', text: '失败' },
};

export default function EditTaskPanel() {
  const [tasks, setTasks] = useState<EditTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await listEditTasks();
      setTasks(data);
    } catch (err) { handleApiError(err, '加载任务列表失败'); }
    setLoading(false);
  }, []);

  useEffect(() => { fetchTasks(); }, [fetchTasks]);

  // Poll every 10 seconds when there are processing/pending tasks
  useEffect(() => {
    const hasActive = tasks.some(t => t.status === 'pending' || t.status === 'processing');
    if (!hasActive) return;
    const interval = setInterval(fetchTasks, 10000);
    return () => clearInterval(interval);
  }, [tasks, fetchTasks]);

  const columns: ColumnsType<EditTask> = [
    { title: '素材', dataIndex: 'material_ids', key: 'materials', width: 80,
      render: (ids: string[]) => `${ids.length}段` },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (s: string) => <Tag color={statusMap[s]?.color}>{statusMap[s]?.text}</Tag> },
    { title: '进度', dataIndex: 'progress', key: 'progress', width: 200, render: (p: number) => (
      <Progress percent={p} size="small" status={p === 100 ? 'success' : p > 0 ? 'active' : undefined} />)
    },
    { title: '产出', dataIndex: 'output_urls', key: 'output', width: 80,
      render: (urls: string[]) => urls.length ? `${urls.length}条` : '-' },
    { title: '创建时间', dataIndex: 'created_at', key: 'time', width: 160,
      render: (d: string) => new Date(d).toLocaleString() },
    { title: '操作', key: 'action', width: 140, render: (_, record) => (
      <div style={{ display: 'flex', gap: 4 }}>
        {record.status === 'done' && record.output_urls.length > 0 && (
          <>
            <Button size="small" icon={<EyeOutlined />}
              onClick={() => { setPreviewUrl(record.output_urls[0]); setPreviewOpen(true); }}>
              预览
            </Button>
            <Button size="small" icon={<DownloadOutlined />}
              onClick={() => { const a = document.createElement('a'); a.href = record.output_urls[0]; a.download = 'video.mp4'; a.click(); }}>
              下载
            </Button>
          </>
        )}
        {record.status === 'failed' && (
          <Button size="small" onClick={() => alert(record.error_message)}>查看原因</Button>
        )}
      </div>
    )},
  ];

  return (
    <Card title="混剪任务">
      <Button type="primary" icon={<PlusOutlined />} style={{ marginBottom: 16 }}
        onClick={() => setWizardOpen(true)}>
        创建剪辑任务
      </Button>
      <Table columns={columns} dataSource={tasks} rowKey="id" loading={loading} size="small"
        locale={{ emptyText: '还没有混剪任务，点击上方按钮创建' }} />

      <EditTaskWizard open={wizardOpen} onClose={() => setWizardOpen(false)}
        onCreated={fetchTasks} />
      <VideoPreview url={previewUrl} visible={previewOpen} onClose={() => setPreviewOpen(false)} />
    </Card>
  );
}
