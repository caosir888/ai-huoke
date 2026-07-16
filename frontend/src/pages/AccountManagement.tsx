import { useState, useEffect } from 'react';
import { Card, Table, Tag, Button, Modal, Select, Input, message, Space, Popconfirm } from 'antd';
import { PlusOutlined, DeleteOutlined, ReloadOutlined, LinkOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { listAccounts, bindAccount, unbindAccount, getDouyinAuthUrl } from '../api/platform';
import { handleApiError, showSuccess } from '../utils/errorHandler';

const platformNames: Record<string, string> = {
  douyin: '抖音', kuaishou: '快手', xhs: '小红书', shipinhao: '视频号',
};

const platformColors: Record<string, string> = {
  douyin: '#000', kuaishou: '#f50', xhs: '#ff2442', shipinhao: '#07c160',
};

const statusText: Record<string, string> = {
  active: '已授权', pending: '待授权', expired: '已过期',
};

const statusColors: Record<string, string> = {
  active: 'success', pending: 'warning', expired: 'error',
};

export default function AccountManagement() {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [bindOpen, setBindOpen] = useState(false);
  const [platform, setPlatform] = useState('kuaishou');
  const [authToken, setAuthToken] = useState('');
  const [oauthLoading, setOauthLoading] = useState(false);

  const fetchAccounts = async () => {
    setLoading(true);
    try {
      const { data } = await listAccounts();
      setAccounts(data);
    } catch (err) { handleApiError(err, '加载账号列表失败'); }
    setLoading(false);
  };

  useEffect(() => {
    fetchAccounts();

    // Handle OAuth callback via postMessage from popup
    const handleMessage = (e: MessageEvent) => {
      if (e.data?.type !== 'oauth_callback') return;
      if (e.data.status === 'success') {
        const platform = e.data.platform || 'douyin';
        showSuccess(`${platformNames[platform] || '平台'}账号授权成功`);
        fetchAccounts();
      } else if (e.data.status === 'error') {
        message.error(e.data.error || '授权失败');
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  const handleDouyinOAuth = async () => {
    setOauthLoading(true);
    try {
      const { data } = await getDouyinAuthUrl();
      // Open Douyin authorization in a popup
      const width = 600;
      const height = 700;
      const left = window.screenX + (window.outerWidth - width) / 2;
      const top = window.screenY + (window.outerHeight - height) / 2;
      const popup = window.open(
        data.authorize_url,
        'douyin_oauth',
        `width=${width},height=${height},left=${left},top=${top}`
      );
      if (!popup) {
        message.warning('请允许弹窗后重试，或手动复制授权链接在新窗口打开');
      }
    } catch (err) { handleApiError(err, '获取授权链接失败'); }
    setOauthLoading(false);
  };

  const handleBind = async () => {
    if (!authToken.trim()) { message.warning('请输入授权Token'); return; }
    try {
      await bindAccount(platform, authToken);
      showSuccess(`${platformNames[platform]}账号绑定成功`);
      setBindOpen(false);
      setAuthToken('');
      fetchAccounts();
    } catch (err) { handleApiError(err, '绑定失败'); }
  };

  const handleUnbind = async (id: string) => {
    try {
      await unbindAccount(id);
      showSuccess('已解绑');
      fetchAccounts();
    } catch (err) { handleApiError(err, '解绑失败'); }
  };

  const columns: ColumnsType<any> = [
    { title: '平台', dataIndex: 'platform', key: 'platform', width: 100,
      render: (p: string) => <Tag color={platformColors[p]}>{platformNames[p]}</Tag> },
    { title: '账号名称', dataIndex: 'account_name', key: 'name' },
    { title: '头像', dataIndex: 'avatar', key: 'avatar', width: 60,
      render: (a: string) => a ? <img src={a} style={{ width: 32, borderRadius: '50%' }} /> : '-' },
    { title: '粉丝数', dataIndex: 'fans_count', key: 'fans', width: 100,
      render: (f: number) => f > 0 ? f.toLocaleString() : '-' },
    { title: '状态', dataIndex: 'auth_status', key: 'status', width: 100,
      render: (s: string) => <Tag color={statusColors[s]}>{statusText[s]}</Tag> },
    { title: '绑定时间', dataIndex: 'created_at', key: 'time', width: 160,
      render: (d: string) => new Date(d).toLocaleString() },
    { title: '操作', key: 'action', width: 80, render: (_, record) => (
      <Popconfirm title="确定解绑？" onConfirm={() => handleUnbind(record.id)}>
        <Button size="small" danger icon={<DeleteOutlined />}>解绑</Button>
      </Popconfirm>
    )},
  ];

  return (
    <div>
      <h2>账号管理</h2>
      <Card title="已绑定账号" extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchAccounts}>刷新</Button>
          <Button
            type="primary"
            icon={<LinkOutlined />}
            onClick={handleDouyinOAuth}
            loading={oauthLoading}
            style={{ background: '#000', borderColor: '#000' }}
          >
            抖音授权登录
          </Button>
          <Button icon={<PlusOutlined />} onClick={() => {
            setPlatform('kuaishou');
            setBindOpen(true);
          }}>
            绑定其他平台
          </Button>
        </Space>
      }>
        <Table columns={columns} dataSource={accounts} rowKey="id" loading={loading} size="small"
          locale={{ emptyText: '还没有绑定任何平台账号' }} />
      </Card>

      <Modal title="绑定平台账号" open={bindOpen} onCancel={() => setBindOpen(false)}
        onOk={handleBind} okText="绑定" width={450}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <label>选择平台</label>
          <Select value={platform} onChange={setPlatform}
            options={Object.entries(platformNames)
              .filter(([k]) => k !== 'douyin')
              .map(([k, v]) => ({ label: v, value: k }))}
            style={{ width: '100%' }} />
          <label>授权Token</label>
          <Input.TextArea placeholder="粘贴平台授权Token或扫码后获取的授权码"
            value={authToken} onChange={e => setAuthToken(e.target.value)} rows={3} />
          <p style={{ color: '#999', fontSize: 12 }}>
            抖音请使用「抖音授权登录」按钮进行 OAuth 授权。
          </p>
        </div>
      </Modal>
    </div>
  );
}
