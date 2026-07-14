import { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Table, Spin, Button, message } from 'antd';
import {
  PlayCircleOutlined, LikeOutlined, CommentOutlined,
  ShareAltOutlined, RiseOutlined, FireOutlined, DownloadOutlined,
} from '@ant-design/icons';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Legend } from 'recharts';
import api from '../api/client';

interface Analytics {
  summary: {
    total_publishes: number;
    total_plays: number;
    total_likes: number;
    total_comments: number;
    total_shares: number;
    engagement_rate: number;
  };
  daily_trend: { date: string; publishes: number; plays: number; likes: number }[];
  platform_breakdown: { platform: string; count: number; plays: number; likes: number }[];
  top_videos: { task_id: string; plays: number; likes: number; comments: number; shares: number }[];
}

function fmt(n: number): string {
  if (n >= 10000) return (n / 10000).toFixed(1) + '万';
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
  return String(n);
}

export default function Analytics() {
  const [data, setData] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const res = await api.get('/publish/analytics');
        setData(res.data);
      } catch { /* ignore */ }
      setLoading(false);
    })();
  }, []);

  const s = data?.summary;

  const topColumns = [
    { title: '视频ID', dataIndex: 'task_id', key: 'id', width: 120,
      render: (id: string) => id.slice(0, 8) },
    { title: '播放', dataIndex: 'plays', key: 'plays', sorter: (a: any, b: any) => b.plays - a.plays },
    { title: '点赞', dataIndex: 'likes', key: 'likes' },
    { title: '评论', dataIndex: 'comments', key: 'comments' },
    { title: '分享', dataIndex: 'shares', key: 'shares' },
  ];

  return (
    <Spin spinning={loading}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0 }}>数据分析</h2>
        <Button icon={<DownloadOutlined />} onClick={async () => {
          try {
            const token = localStorage.getItem('token');
            const res = await fetch('http://localhost:8000/publish/analytics/export', {
              headers: { Authorization: `Bearer ${token}` },
            });
            if (!res.ok) throw new Error();
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `analytics_export_${new Date().toISOString().slice(0, 10)}.csv`;
            a.click();
            URL.revokeObjectURL(url);
            message.success('导出成功');
          } catch { message.error('导出失败'); }
        }}>导出 CSV</Button>
      </div>

      {/* Summary Cards */}
      <Row gutter={[16, 16]}>
        <Col xs={12} sm={8} md={4}>
          <Card><Statistic title="总发布数" value={s?.total_publishes || 0} prefix={<FireOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card><Statistic title="总播放量" value={s?.total_plays || 0} prefix={<PlayCircleOutlined />} formatter={v => fmt(Number(v))} /></Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card><Statistic title="总点赞" value={s?.total_likes || 0} prefix={<LikeOutlined />} formatter={v => fmt(Number(v))} /></Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card><Statistic title="总评论" value={s?.total_comments || 0} prefix={<CommentOutlined />} formatter={v => fmt(Number(v))} /></Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card><Statistic title="总分享" value={s?.total_shares || 0} prefix={<ShareAltOutlined />} formatter={v => fmt(Number(v))} /></Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card>
            <Statistic title="互动率" value={s?.engagement_rate || 0}
              prefix={<RiseOutlined />} suffix="%" precision={2}
              valueStyle={{ color: (s?.engagement_rate || 0) > 5 ? '#52c41a' : '#1677ff' }} />
          </Card>
        </Col>
      </Row>

      {/* Trend Chart */}
      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={16}>
          <Card title="每日趋势（近14天）">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={data?.daily_trend || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="plays" stroke="#1677ff" name="播放" strokeWidth={2} />
                <Line type="monotone" dataKey="likes" stroke="#52c41a" name="点赞" strokeWidth={2} />
                <Line type="monotone" dataKey="publishes" stroke="#fa8c16" name="发布数" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col span={8}>
          <Card title="平台分布">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={data?.platform_breakdown || []} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis dataKey="platform" type="category" tick={{ fontSize: 12 }} width={50} />
                <Tooltip />
                <Bar dataKey="plays" fill="#1677ff" name="播放" />
                <Bar dataKey="count" fill="#52c41a" name="发布数" />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      {/* Top Videos */}
      <Card title="热门视频 TOP 10" style={{ marginTop: 24 }}>
        <Table
          columns={topColumns}
          dataSource={data?.top_videos || []}
          rowKey="task_id"
          size="small"
          pagination={false}
          locale={{ emptyText: '暂无发布数据，去发布一些视频吧' }}
        />
      </Card>
    </Spin>
  );
}
