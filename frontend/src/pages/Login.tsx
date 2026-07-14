import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Input, Button, message, Typography } from 'antd';
import { PhoneOutlined, LockOutlined } from '@ant-design/icons';
import { sendCode, login } from '../api/auth';
import { useAuthStore } from '../stores/authStore';

const { Title } = Typography;

export default function Login() {
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const navigate = useNavigate();
  const { fetchUser } = useAuthStore();

  const handleSendCode = async () => {
    if (!/^1[3-9]\d{9}$/.test(phone)) {
      message.error('请输入正确的手机号');
      return;
    }
    setSending(true);
    try {
      const { data } = await sendCode(phone);
      const msg = data.debug_code ? `验证码已发送（调试：${data.debug_code}）` : '验证码已发送';
      message.success(msg);
      setCountdown(60);
      const timer = setInterval(() => {
        setCountdown((c) => { if (c <= 1) { clearInterval(timer); return 0; } return c - 1; });
      }, 1000);
    } catch (err: any) {
      message.error(err.friendlyMessage || '发送失败');
    }
    setSending(false);
  };

  const handleLogin = async () => {
    setLoading(true);
    try {
      const { data } = await login(phone, code);
      localStorage.setItem('token', data.access_token);
      await fetchUser();
      message.success('登录成功');
      navigate('/');
    } catch (err: any) {
      message.error(err.friendlyMessage || '登录失败，请检查验证码');
    }
    setLoading(false);
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    }}>
      <Card style={{ width: 400, borderRadius: 12 }}>
        <Title level={3} style={{ textAlign: 'center', marginBottom: 32 }}>AI获客</Title>
        <Input
          size="large" prefix={<PhoneOutlined />} placeholder="手机号"
          value={phone} onChange={(e) => setPhone(e.target.value)}
          style={{ marginBottom: 16 }}
        />
        <Input
          size="large" prefix={<LockOutlined />} placeholder="验证码"
          value={code} onChange={(e) => setCode(e.target.value)}
          suffix={
            <Button type="link" loading={sending} disabled={countdown > 0}
              onClick={handleSendCode}>
              {countdown > 0 ? `${countdown}s` : '发送验证码'}
            </Button>
          }
          style={{ marginBottom: 24 }}
        />
        <Button type="primary" size="large" block loading={loading}
          onClick={handleLogin}>
          登录 / 注册
        </Button>
      </Card>
    </div>
  );
}
