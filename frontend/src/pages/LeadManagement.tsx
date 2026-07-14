import { useState, useEffect, useCallback } from 'react';
import { Card, Table, Tag, Button, Modal, Input, Select, Tabs, Space, message, Spin, Statistic, Row, Col, Switch, Form, Empty, Popconfirm, Typography, Badge } from 'antd';
import { PlusOutlined, CopyOutlined, AimOutlined, LinkOutlined, SendOutlined, MessageOutlined, PictureOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import api from '../api/client';

const { TextArea } = Input;
const { Paragraph } = Typography;

const statusColors: Record<string, string> = { new: 'blue', contacted: 'orange', qualified: 'purple', converted: 'green', lost: 'red' };
const statusNames: Record<string, string> = { new: '新线索', contacted: '已联系', qualified: '已验证', converted: '已转化', lost: '已流失' };
const sourceColors: Record<string, string> = { form: 'blue', video: 'purple', manual: 'default' };
const sourceNames: Record<string, string> = { form: '表单', video: '视频', manual: '手动' };

const FIELD_OPTIONS = [
  { label: '姓名', value: 'name' },
  { label: '手机号', value: 'phone' },
  { label: '公司', value: 'company' },
  { label: '留言', value: 'message' },
];

export default function LeadManagement() {
  const [leads, setLeads] = useState<any[]>([]);
  const [forms, setForms] = useState<any[]>([]);
  const [stats, setStats] = useState<any>({});
  const [loading, setLoading] = useState(false);
  const [statsLoading, setStatsLoading] = useState(false);
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [editingLead, setEditingLead] = useState<any>(null);
  const [leadModalOpen, setLeadModalOpen] = useState(false);
  const [leadNote, setLeadNote] = useState('');
  const [leadFilter, setLeadFilter] = useState<any>({});
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [newForm, setNewForm] = useState<any>({ title: '', description: '', fields: ['name', 'phone', 'company'], video_url: '', is_active: true });
  const [submitting, setSubmitting] = useState(false);

  // Outreach state
  const [outreachStats, setOutreachStats] = useState<any>({});
  const [templates, setTemplates] = useState<any[]>([]);
  const [outreachTasks, setOutreachTasks] = useState<any[]>([]);
  const [outreachTotal, setOutreachTotal] = useState(0);
  const [outreachPage, setOutreachPage] = useState(1);
  const [outreachLoading, setOutreachLoading] = useState(false);
  const [tplModalOpen, setTplModalOpen] = useState(false);
  const [editingTpl, setEditingTpl] = useState<any>(null);
  const [outreachModalOpen, setOutreachModalOpen] = useState(false);
  const [selectedLeads, setSelectedLeads] = useState<string[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [executing, setExecuting] = useState(false);

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: '20' });
      if (leadFilter.status) params.set('status', leadFilter.status);
      if (leadFilter.source) params.set('source', leadFilter.source);
      if (leadFilter.form_id) params.set('form_id', leadFilter.form_id);
      const { data } = await api.get(`/leads?${params.toString()}`);
      setLeads(data.items);
      setTotal(data.total);
    } catch { /* ignore */ }
    setLoading(false);
  }, [page, leadFilter]);

  const fetchForms = useCallback(async () => {
    try {
      const { data } = await api.get('/leads/forms');
      setForms(data);
    } catch { /* ignore */ }
  }, []);

  const fetchStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const { data } = await api.get('/leads/stats');
      setStats(data);
    } catch { /* ignore */ }
    setStatsLoading(false);
  }, []);

  useEffect(() => { fetchLeads(); fetchForms(); fetchStats(); }, [fetchLeads, fetchForms, fetchStats]);

  // Outreach data fetching
  const fetchOutreachStats = useCallback(async () => {
    try { const { data } = await api.get('/outreach/stats'); setOutreachStats(data); } catch { /* ignore */ }
  }, []);
  const fetchTemplates = useCallback(async () => {
    try { const { data } = await api.get('/outreach/templates'); setTemplates(data); } catch { /* ignore */ }
  }, []);
  const fetchOutreachTasks = useCallback(async () => {
    setOutreachLoading(true);
    try {
      const { data } = await api.get(`/outreach/tasks?page=${outreachPage}&page_size=20`);
      setOutreachTasks(data.items);
      setOutreachTotal(data.total);
    } catch { /* ignore */ }
    setOutreachLoading(false);
  }, [outreachPage]);

  const handleSaveTemplate = async () => {
    if (!editingTpl?.name?.trim()) { message.error('请输入模板名称'); return; }
    try {
      if (editingTpl.id) {
        await api.put(`/outreach/templates/${editingTpl.id}`, { name: editingTpl.name, content: editingTpl.content, image_url: editingTpl.image_url });
        message.success('模板已更新');
      } else {
        await api.post('/outreach/templates', { name: editingTpl.name, content: editingTpl.content, image_url: editingTpl.image_url, platform: 'douyin' });
        message.success('模板已创建');
      }
      setTplModalOpen(false); setEditingTpl(null); fetchTemplates();
    } catch (err: any) { message.error(err.friendlyMessage || '保存失败'); }
  };

  const handleDeleteTemplate = async (id: string) => {
    try { await api.delete(`/outreach/templates/${id}`); message.success('已删除'); fetchTemplates(); } catch { /* ignore */ }
  };

  const handleCreateOutreach = async () => {
    if (selectedLeads.length === 0) { message.error('请选择要触达的线索'); return; }
    if (!selectedTemplate) { message.error('请选择话术模板'); return; }
    try {
      const { data } = await api.post('/outreach/send', { lead_ids: selectedLeads, template_id: selectedTemplate });
      message.success(`已创建 ${data.created} 个触达任务`);
      setOutreachModalOpen(false); setSelectedLeads([]); setSelectedTemplate('');
      fetchOutreachTasks(); fetchOutreachStats();
    } catch (err: any) { message.error(err.friendlyMessage || '创建失败'); }
  };

  const handleExecuteOutreach = async () => {
    setExecuting(true);
    try {
      const { data } = await api.post('/outreach/execute');
      message.success(data.message);
      fetchOutreachTasks(); fetchOutreachStats();
    } catch (err: any) { message.error(err.friendlyMessage || '执行失败'); }
    setExecuting(false);
  };

  const handleCreateForm = async () => {
    if (!newForm.title.trim()) { message.error('请输入表单标题'); return; }
    setSubmitting(true);
    try {
      const { data } = await api.post('/leads/forms', newForm);
      message.success('表单创建成功');
      setFormModalOpen(false);
      setNewForm({ title: '', description: '', fields: ['name', 'phone', 'company'], video_url: '', is_active: true });
      const shareLink = `${window.location.origin}/form/${data.share_code}`;
      Modal.info({
        title: '分享链接',
        content: <div><Input value={shareLink} readOnly /><Button icon={<CopyOutlined />} onClick={() => { navigator.clipboard.writeText(shareLink); message.success('已复制'); }} style={{ marginTop: 8 }}>复制链接</Button></div>,
      });
      fetchForms();
    } catch (err: any) { message.error(err.friendlyMessage || '创建失败'); }
    setSubmitting(false);
  };

  const handleUpdateLead = async () => {
    if (!editingLead) return;
    try {
      await api.put(`/leads/${editingLead.id}`, { status: editingLead.status, notes: leadNote });
      message.success('已更新');
      setLeadModalOpen(false);
      setEditingLead(null);
      fetchLeads();
      fetchStats();
    } catch (err: any) { message.error(err.friendlyMessage || '更新失败'); }
  };

  const handleDeleteLead = async (id: string) => {
    try {
      await api.delete(`/leads/${id}`);
      message.success('已删除');
      fetchLeads();
      fetchStats();
    } catch { /* ignore */ }
  };

  const handleToggleForm = async (form: any) => {
    try {
      await api.put(`/leads/forms/${form.id}`, { is_active: !form.is_active });
      fetchForms();
    } catch { /* ignore */ }
  };

  const handleDeleteForm = async (id: string) => {
    try {
      await api.delete(`/leads/forms/${id}`);
      message.success('已删除');
      fetchForms();
      fetchStats();
    } catch { /* ignore */ }
  };

  const copyShareLink = (code: string) => {
    const link = `${window.location.origin}/form/${code}`;
    navigator.clipboard.writeText(link).then(() => message.success('链接已复制'));
  };

  const leadColumns = [
    { title: '姓名', dataIndex: 'name', key: 'name', width: 100, render: (v: string) => v || '-' },
    { title: '手机号', dataIndex: 'phone', key: 'phone', width: 130, render: (v: string) => v || '-' },
    { title: '公司', dataIndex: 'company', key: 'company', width: 120, render: (v: string) => v || '-', ellipsis: true },
    { title: '来源', dataIndex: 'source', key: 'source', width: 80, render: (v: string) => <Tag color={sourceColors[v]}>{sourceNames[v] || v}</Tag> },
    { title: '表单', dataIndex: 'form_title', key: 'form', width: 100, render: (v: string) => v || '-', ellipsis: true },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90,
      render: (v: string) => <Tag color={statusColors[v]}>{statusNames[v] || v}</Tag> },
    { title: '备注', dataIndex: 'notes', key: 'notes', width: 150, render: (v: string) => v || '-', ellipsis: true },
    { title: '时间', dataIndex: 'created_at', key: 'time', width: 110,
      render: (d: string) => dayjs(d).format('MM-DD HH:mm') },
    { title: '操作', key: 'actions', width: 140,
      render: (_: any, r: any) => (
        <Space>
          <Button type="link" size="small" onClick={() => { setEditingLead({ ...r }); setLeadNote(r.notes || ''); setLeadModalOpen(true); }}>跟进</Button>
          <Popconfirm title="确认删除？" onConfirm={() => handleDeleteLead(r.id)}>
            <Button type="link" size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <h2><AimOutlined /> 获客管理</h2>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}><Card><Statistic title="总线索" value={stats.total || 0} loading={statsLoading} /></Card></Col>
        <Col span={6}><Card><Statistic title="今日新增" value={stats.today_new || 0} loading={statsLoading} /></Card></Col>
        <Col span={6}><Card><Statistic title="转化率" value={stats.conversion_rate || 0} suffix="%" precision={1} loading={statsLoading} /></Card></Col>
        <Col span={6}><Card><Statistic title="跟进中" value={stats.contacted || 0} loading={statsLoading} /></Card></Col>
      </Row>

      <Tabs defaultActiveKey="leads" onChange={(key) => {
        if (key === 'outreach') { fetchOutreachTasks(); fetchOutreachStats(); fetchTemplates(); fetchLeads(); }
      }} items={[
        {
          key: 'leads',
          label: '线索列表',
          children: (
            <Card>
              <Space style={{ marginBottom: 16 }}>
                <Select placeholder="状态筛选" allowClear style={{ width: 120 }} value={leadFilter.status}
                  onChange={(v) => { setLeadFilter((f: any) => ({ ...f, status: v })); setPage(1); }}
                  options={Object.entries(statusNames).map(([k, v]) => ({ value: k, label: v }))} />
                <Select placeholder="来源筛选" allowClear style={{ width: 120 }} value={leadFilter.source}
                  onChange={(v) => { setLeadFilter((f: any) => ({ ...f, source: v })); setPage(1); }}
                  options={Object.entries(sourceNames).map(([k, v]) => ({ value: k, label: v }))} />
                <Select placeholder="表单筛选" allowClear style={{ width: 160 }} value={leadFilter.form_id}
                  onChange={(v) => { setLeadFilter((f: any) => ({ ...f, form_id: v })); setPage(1); }}
                  options={forms.map((f: any) => ({ value: f.id, label: f.title }))} />
                <Button type="primary" icon={<PlusOutlined />}
                  onClick={() => { setEditingLead({ status: 'new', source: 'manual' }); setLeadNote(''); setLeadModalOpen(true); }}>
                  手动创建线索
                </Button>
              </Space>
              <Spin spinning={loading}>
                <Table columns={leadColumns} dataSource={leads} rowKey="id" size="small"
                  locale={{ emptyText: '暂无线索数据' }}
                  pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 条` }} />
              </Spin>
            </Card>
          ),
        },
        {
          key: 'outreach',
          label: '触达中心',
          children: (
            <div>
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={4}><Card size="small"><Statistic title="总触达" value={outreachStats.total || 0} /></Card></Col>
                <Col span={4}><Card size="small"><Statistic title="今日已发" value={outreachStats.today || 0} styles={{ content: { color: '#1890ff' } }} /></Card></Col>
                <Col span={4}><Card size="small"><Statistic title="已发送" value={outreachStats.sent || 0} styles={{ content: { color: '#52c41a' } }} /></Card></Col>
                <Col span={4}><Card size="small"><Statistic title="待发送" value={outreachStats.pending || 0} styles={{ content: { color: '#faad14' } }} /></Card></Col>
                <Col span={4}><Card size="small"><Statistic title="失败" value={outreachStats.failed || 0} styles={{ content: { color: '#ff4d4f' } }} /></Card></Col>
                <Col span={4}><Card size="small"><Statistic title="已回复" value={outreachStats.replied || 0} styles={{ content: { color: '#722ed1' } }} /></Card></Col>
              </Row>

              <Row gutter={16}>
                <Col span={8}>
                  <Card title="话术模板" size="small" extra={
                    <Button type="link" size="small" icon={<PlusOutlined />}
                      onClick={() => { setEditingTpl({ name: '', content: '', image_url: '' }); setTplModalOpen(true); }}>
                      新建
                    </Button>
                  }>
                    {templates.length === 0 ? (
                      <Empty description="暂无话术模板" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    ) : (
                      <div>
                        {templates.map((t: any) => (
                          <div key={t.id} style={{ display: 'flex', alignItems: 'flex-start', padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
                            <MessageOutlined style={{ fontSize: 18, color: '#1890ff', marginRight: 10, marginTop: 4 }} />
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div style={{ fontWeight: 500 }}>{t.name} <Badge count={t.usage_count} overflowCount={999} style={{ backgroundColor: '#52c41a' }} /></div>
                              <Paragraph ellipsis={{ rows: 2 }} style={{ marginBottom: 0, fontSize: 12, color: '#999' }}>{t.content}</Paragraph>
                            </div>
                            <div style={{ flexShrink: 0, marginLeft: 8 }}>
                              <Button type="link" size="small" onClick={() => { setEditingTpl({ ...t }); setTplModalOpen(true); }}>编辑</Button>
                              <Popconfirm title="确认删除？" onConfirm={() => handleDeleteTemplate(t.id)}>
                                <Button type="link" size="small" danger>删除</Button>
                              </Popconfirm>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>
                </Col>

                <Col span={16}>
                  <Card title="触达任务" size="small" extra={
                    <Space>
                      <Button icon={<SendOutlined />} onClick={() => { fetchOutreachTasks(); fetchOutreachStats(); fetchTemplates(); setOutreachModalOpen(true); }}>
                        新建触达任务
                      </Button>
                      <Button type="primary" icon={<SendOutlined />} loading={executing}
                        onClick={handleExecuteOutreach}
                        disabled={!outreachStats.pending || outreachStats.pending === 0}>
                        执行待发任务
                      </Button>
                    </Space>
                  }>
                    <Spin spinning={outreachLoading}>
                      <Table columns={[
                        { title: '线索', dataIndex: 'lead_name', key: 'lead', width: 80, render: (v: string) => v || '-' },
                        { title: '手机', dataIndex: 'lead_phone', key: 'phone', width: 110, render: (v: string) => v || '-' },
                        { title: '话术', dataIndex: 'template_name', key: 'tpl', width: 100, render: (v: string) => v || '-', ellipsis: true },
                        { title: '平台', dataIndex: 'platform', key: 'plat', width: 70 },
                        { title: '状态', dataIndex: 'status', key: 'status', width: 80,
                          render: (v: string) => {
                            const m: Record<string, string> = { pending: '待发送', sent: '已发送', failed: '失败', replied: '已回复' };
                            const c: Record<string, string> = { pending: 'default', sent: 'green', failed: 'red', replied: 'purple' };
                            return <Tag color={c[v]}>{m[v] || v}</Tag>;
                          }},
                        { title: '结果', dataIndex: 'result_message', key: 'result', width: 180, render: (v: string) => v || '-', ellipsis: true },
                        { title: '时间', dataIndex: 'created_at', key: 'time', width: 110, render: (d: string) => dayjs(d).format('MM-DD HH:mm') },
                      ]} dataSource={outreachTasks} rowKey="id" size="small"
                        locale={{ emptyText: '暂无触达任务' }}
                        pagination={{ current: outreachPage, total: outreachTotal, pageSize: 20, onChange: setOutreachPage, showTotal: (t: number) => `共 ${t} 条` }} />
                    </Spin>
                  </Card>
                </Col>
              </Row>
            </div>
          ),
        },
        {
          key: 'forms',
          label: '获客表单',
          children: (
            <Card extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setFormModalOpen(true)}>新建表单</Button>}>
              {forms.length === 0 ? (
                <Empty description="暂无获客表单，点击右上角创建" />
              ) : (
                <Row gutter={[16, 16]}>
                  {forms.map((f: any) => (
                    <Col xs={24} sm={12} md={8} key={f.id}>
                      <Card
                        title={f.title}
                        size="small"
                        extra={<Switch checked={f.is_active} onChange={() => handleToggleForm(f)} />}
                        actions={[
                          <Button type="link" icon={<LinkOutlined />} onClick={() => copyShareLink(f.share_code)}>复制链接</Button>,
                          <Popconfirm title="确认删除？" onConfirm={() => handleDeleteForm(f.id)}>
                            <Button type="link" danger>删除</Button>
                          </Popconfirm>,
                        ]}
                      >
                        <p style={{ color: '#999', fontSize: 12 }}>{f.description || '无描述'}</p>
                        <p style={{ fontSize: 12 }}>已收集: <b>{f.lead_count}</b> 条线索</p>
                        <p style={{ fontSize: 12, color: '#999' }}>{dayjs(f.created_at).format('YYYY-MM-DD HH:mm')}</p>
                      </Card>
                    </Col>
                  ))}
                </Row>
              )}
            </Card>
          ),
        },
      ]} />

      {/* Lead Edit Modal */}
      <Modal title={editingLead?.id ? '编辑线索' : '新建线索'} open={leadModalOpen}
        onCancel={() => { setLeadModalOpen(false); setEditingLead(null); }}
        onOk={handleUpdateLead}
        okText="保存" cancelText="取消"
      >
        <Form layout="vertical">
          <Form.Item label="姓名">
            <Input value={editingLead?.name || ''} onChange={(e) => setEditingLead((v: any) => ({ ...v, name: e.target.value }))} />
          </Form.Item>
          <Form.Item label="手机号">
            <Input value={editingLead?.phone || ''} onChange={(e) => setEditingLead((v: any) => ({ ...v, phone: e.target.value }))} />
          </Form.Item>
          <Form.Item label="公司">
            <Input value={editingLead?.company || ''} onChange={(e) => setEditingLead((v: any) => ({ ...v, company: e.target.value }))} />
          </Form.Item>
          <Form.Item label="状态">
            <Select value={editingLead?.status || 'new'} onChange={(v) => setEditingLead((p: any) => ({ ...p, status: v }))}
              options={Object.entries(statusNames).map(([k, v]) => ({ value: k, label: v }))} />
          </Form.Item>
          <Form.Item label="跟进备注">
            <Input.TextArea rows={3} value={leadNote} onChange={(e) => setLeadNote(e.target.value)} placeholder="添加跟进备注..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* Template Edit Modal */}
      <Modal title={editingTpl?.id ? '编辑话术模板' : '新建话术模板'} open={tplModalOpen}
        onCancel={() => { setTplModalOpen(false); setEditingTpl(null); }}
        onOk={handleSaveTemplate}
        okText="保存" cancelText="取消"
      >
        <Form layout="vertical">
          <Form.Item label="模板名称" required>
            <Input value={editingTpl?.name || ''} onChange={(e) => setEditingTpl((v: any) => ({ ...v, name: e.target.value }))} placeholder="如：首次问候" />
          </Form.Item>
          <Form.Item label="话术内容" required>
            <TextArea rows={4} value={editingTpl?.content || ''} onChange={(e) => setEditingTpl((v: any) => ({ ...v, content: e.target.value }))}
              placeholder="如：您好，我是XX公司的，看到您对我们的产品感兴趣..." />
          </Form.Item>
          <Form.Item label="图片URL（可选）">
            <Input value={editingTpl?.image_url || ''} onChange={(e) => setEditingTpl((v: any) => ({ ...v, image_url: e.target.value }))}
              placeholder="https://... 引流图片或二维码" prefix={<PictureOutlined />} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Outreach Create Modal */}
      <Modal title="新建触达任务" open={outreachModalOpen} width={640}
        onCancel={() => setOutreachModalOpen(false)}
        onOk={handleCreateOutreach}
        okText="创建任务" cancelText="取消"
      >
        <Form layout="vertical">
          <Form.Item label="选择话术模板" required>
            <Select value={selectedTemplate || undefined} onChange={setSelectedTemplate}
              placeholder="选择要发送的话术"
              options={templates.map((t: any) => ({ value: t.id, label: `${t.name} (已用${t.usage_count}次)` }))} />
          </Form.Item>
          <Form.Item label="选择目标线索" required>
            <Select mode="multiple" value={selectedLeads} onChange={setSelectedLeads}
              placeholder="选择要触达的线索（可多选）" style={{ width: '100%' }}
              options={leads.map((l: any) => ({ value: l.id, label: `${l.name || '未命名'} - ${l.phone || '无手机'} [${statusNames[l.status] || l.status}]` }))}
              filterOption={(input, option) => (option?.label as string || '').includes(input)} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Form Create Modal */}
      <Modal title="新建获客表单" open={formModalOpen}
        onCancel={() => setFormModalOpen(false)}
        onOk={handleCreateForm}
        confirmLoading={submitting}
        okText="创建" cancelText="取消"
      >
        <Form layout="vertical">
          <Form.Item label="表单标题" required>
            <Input value={newForm.title} onChange={(e) => setNewForm((f: any) => ({ ...f, title: e.target.value }))} placeholder="例如：产品咨询" />
          </Form.Item>
          <Form.Item label="描述">
            <Input value={newForm.description} onChange={(e) => setNewForm((f: any) => ({ ...f, description: e.target.value }))} placeholder="可选描述" />
          </Form.Item>
          <Form.Item label="收集字段">
            <Select mode="multiple" value={newForm.fields} onChange={(v) => setNewForm((f: any) => ({ ...f, fields: v }))} options={FIELD_OPTIONS} />
          </Form.Item>
          <Form.Item label="关联视频URL">
            <Input value={newForm.video_url} onChange={(e) => setNewForm((f: any) => ({ ...f, video_url: e.target.value }))} placeholder="可选" />
          </Form.Item>
          <Form.Item label="启用">
            <Switch checked={newForm.is_active} onChange={(v) => setNewForm((f: any) => ({ ...f, is_active: v }))} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
