import { useState, useEffect } from 'react';
import { Card, Table, Tag, Spin } from 'antd';
import dayjs from 'dayjs';
import api from '../api/client';

const planColors: Record<string, string> = { free: 'default', basic: 'blue', pro: 'purple', enterprise: 'gold' };
const planNames: Record<string, string> = { free: '免费版', basic: '基础版', pro: '专业版', enterprise: '企业版' };

function maskPhone(phone: string) {
  if (!phone || phone.length < 7) return phone;
  return phone.slice(0, 3) + '****' + phone.slice(-4);
}

function fmtBytes(bytes: number) {
  if (bytes >= 1024 ** 3) return (bytes / (1024 ** 3)).toFixed(1) + ' GB';
  if (bytes >= 1024 ** 2) return (bytes / (1024 ** 2)).toFixed(1) + ' MB';
  if (bytes >= 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return bytes + ' B';
}

export default function AdminUsers() {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const { data } = await api.get('/admin/users');
        setUsers(data);
      } catch { /* ignore */ }
      setLoading(false);
    })();
  }, []);

  const columns = [
    { title: '手机号', dataIndex: 'phone', key: 'phone', width: 140,
      render: (p: string) => maskPhone(p) },
    { title: '行业', dataIndex: 'industry', key: 'industry', width: 100,
      render: (v: string) => v || '-' },
    { title: '公司', dataIndex: 'company_name', key: 'company', width: 120,
      render: (v: string) => v || '-', ellipsis: true },
    { title: '套餐', dataIndex: 'plan_type', key: 'plan', width: 90,
      render: (v: string) => <Tag color={planColors[v]}>{planNames[v] || v}</Tag> },
    { title: '今日配额', key: 'daily', width: 100,
      render: (_: any, r: any) => `${r.quota?.daily_limit || 3}次/天` },
    { title: '月配额', key: 'monthly', width: 100,
      render: (_: any, r: any) => `${r.quota?.monthly_limit || 30}次/月` },
    { title: '存储用量', key: 'storage', width: 110,
      render: (_: any, r: any) => {
        const used = r.quota?.storage_used || 0;
        const limit = r.quota?.storage_limit || 1073741824;
        const pct = Math.round(used / Math.max(1, limit) * 100);
        return <span>{fmtBytes(used)} <span style={{ color: '#999', fontSize: 11 }}>({pct}%)</span></span>;
      }},
    { title: '注册时间', dataIndex: 'created_at', key: 'time', width: 120,
      render: (d: string) => dayjs(d).format('MM-DD HH:mm') },
  ];

  return (
    <div>
      <h2>用户管理</h2>
      <Card>
        <Spin spinning={loading}>
          <Table
            columns={columns}
            dataSource={users}
            rowKey="id"
            size="small"
            locale={{ emptyText: '暂无注册用户' }}
            summary={() => (
              <Table.Summary.Row>
                <Table.Summary.Cell index={0}>
                  <span style={{ color: '#999' }}>共 {users.length} 位用户</span>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={1} colSpan={8} />
              </Table.Summary.Row>
            )}
          />
        </Spin>
      </Card>
    </div>
  );
}
