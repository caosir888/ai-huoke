import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Form, Input, Button, message, Result, Spin, Typography } from 'antd';
import { SendOutlined } from '@ant-design/icons';
import api from '../api/client';

const { Title, Paragraph } = Typography;

const fieldLabels: Record<string, string> = { name: '姓名', phone: '手机号', company: '公司', message: '留言' };

export default function PublicForm() {
  const { shareCode } = useParams();
  const [formInfo, setFormInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get(`/public/form/${shareCode}`);
        setFormInfo(data);
      } catch (err: any) {
        setError(err.friendlyMessage || '表单不存在');
      }
      setLoading(false);
    })();
  }, [shareCode]);

  const handleSubmit = async (values: any) => {
    setSubmitting(true);
    try {
      await api.post(`/public/form/${shareCode}/submit`, values);
      setSubmitted(true);
    } catch (err: any) {
      message.error(err.friendlyMessage || '提交失败，请重试');
    }
    setSubmitting(false);
  };

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 100 }}><Spin size="large" /></div>;
  if (error) return <Result status="404" title="表单不可用" subTitle={error} />;
  if (submitted) return (
    <Result status="success" title="提交成功" subTitle="我们会尽快与您联系！"
      extra={<Button type="primary" onClick={() => setSubmitted(false)}>继续提交</Button>} />
  );

  return (
    <div style={{ minHeight: '100vh', background: '#f5f5f5', display: 'flex', justifyContent: 'center', paddingTop: 60 }}>
      <Card style={{ width: 420, maxWidth: '90vw', borderRadius: 12, height: 'fit-content' }}>
        <Title level={4} style={{ textAlign: 'center' }}>{formInfo?.title || '信息收集'}</Title>
        {formInfo?.description && <Paragraph type="secondary" style={{ textAlign: 'center' }}>{formInfo.description}</Paragraph>}
        <Form layout="vertical" onFinish={handleSubmit}>
          {formInfo?.fields?.includes('name') && (
            <Form.Item name="name" label="姓名" rules={[{ required: true, message: '请输入姓名' }]}>
              <Input placeholder="请输入您的姓名" />
            </Form.Item>
          )}
          {formInfo?.fields?.includes('phone') && (
            <Form.Item name="phone" label="手机号" rules={[
              { required: true, message: '请输入手机号' },
              { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号' },
            ]}>
              <Input placeholder="请输入您的手机号" />
            </Form.Item>
          )}
          {formInfo?.fields?.includes('company') && (
            <Form.Item name="company" label="公司">
              <Input placeholder="请输入您的公司名称（选填）" />
            </Form.Item>
          )}
          {formInfo?.fields?.includes('message') && (
            <Form.Item name="message" label="留言">
              <Input.TextArea rows={3} placeholder="请输入您的留言（选填）" />
            </Form.Item>
          )}
          <Form.Item>
            <Button type="primary" htmlType="submit" block size="large" loading={submitting} icon={<SendOutlined />}>
              提交
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
