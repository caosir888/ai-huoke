import { Card, Statistic, Row, Col, Table, Tag } from 'antd';
import { PlayCircleOutlined, LikeOutlined, MessageOutlined, ShareAltOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

interface VideoMetric {
  id: string;
  title: string;
  status: string;
  plays: number;
  likes: number;
  comments: number;
  shares: number;
  engagement_rate: number;
  created_at: string;
  platform: string;
}

const platformTags: Record<string, string> = {
  douyin: '抖音', kuaishou: '快手', xhs: '小红书', shipinhao: '视频号',
};

const platformColors: Record<string, string> = {
  douyin: '#000', kuaishou: '#f50', xhs: '#ff2442', shipinhao: '#07c160',
};

export default function VideoDataPanel({ tasks }: { tasks: any[] }) {
  const videos: VideoMetric[] = tasks.map(t => ({
    id: t.id,
    title: t.title || '-',
    status: t.status,
    plays: t.metrics?.plays || 0,
    likes: t.metrics?.likes || 0,
    comments: t.metrics?.comments || 0,
    shares: t.metrics?.shares || 0,
    engagement_rate: t.metrics?.plays
      ? ((t.metrics?.likes || 0) + (t.metrics?.comments || 0) + (t.metrics?.shares || 0)) / t.metrics.plays * 100
      : 0,
    created_at: t.created_at,
    platform: t.platform_account_id || '未知',
  }));

  const totalPlays = videos.reduce((s, v) => s + v.plays, 0);
  const totalLikes = videos.reduce((s, v) => s + v.likes, 0);
  const totalComments = videos.reduce((s, v) => s + v.comments, 0);
  const totalShares = videos.reduce((s, v) => s + v.shares, 0);

  const columns: ColumnsType<VideoMetric> = [
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '平台', dataIndex: 'platform', key: 'platform', width: 80,
      render: (p: string) => <Tag color={platformColors[p] || '#999'}>{platformTags[p] || p}</Tag> },
    { title: '播放', dataIndex: 'plays', key: 'plays', width: 100,
      sorter: (a, b) => a.plays - b.plays,
      render: (v: number) => v.toLocaleString() },
    { title: '点赞', dataIndex: 'likes', key: 'likes', width: 80,
      render: (v: number) => v.toLocaleString() },
    { title: '评论', dataIndex: 'comments', key: 'comments', width: 80,
      render: (v: number) => v.toLocaleString() },
    { title: '分享', dataIndex: 'shares', key: 'shares', width: 80,
      render: (v: number) => v.toLocaleString() },
    { title: '互动率', dataIndex: 'engagement_rate', key: 'rate', width: 80,
      render: (v: number) => `${v.toFixed(1)}%` },
    { title: '发布时间', dataIndex: 'created_at', key: 'time', width: 120,
      render: (d: string) => dayjs(d).format('MM-DD HH:mm') },
  ];

  return (
    <div style={{ marginTop: 24 }}>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card><Statistic title="总播放量" value={totalPlays} prefix={<PlayCircleOutlined />} formatter={(v) => (v as number).toLocaleString()} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="总点赞" value={totalLikes} prefix={<LikeOutlined />} formatter={(v) => (v as number).toLocaleString()} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="总评论" value={totalComments} prefix={<MessageOutlined />} formatter={(v) => (v as number).toLocaleString()} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="总分享" value={totalShares} prefix={<ShareAltOutlined />} formatter={(v) => (v as number).toLocaleString()} /></Card>
        </Col>
      </Row>

      <Card title="视频数据明细">
        <Table columns={columns} dataSource={videos} rowKey="id" size="small"
          locale={{ emptyText: '暂无可展示的视频数据' }} />
      </Card>
    </div>
  );
}
