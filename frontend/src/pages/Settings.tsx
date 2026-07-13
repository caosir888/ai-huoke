import { Card, Descriptions, Button, message } from 'antd';
import { CrownOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

export default function Settings() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  return (
    <div>
      <h2>设置</h2>
      <Card title="个人中心" style={{ maxWidth: 600, marginTop: 24 }}>
        <Descriptions column={1}>
          <Descriptions.Item label="手机号">{user?.phone}</Descriptions.Item>
          <Descriptions.Item label="行业">{user?.industry || '未设置'}</Descriptions.Item>
          <Descriptions.Item label="公司名称">{user?.company_name || '未设置'}</Descriptions.Item>
          <Descriptions.Item label="套餐">
            {user?.plan_type === 'free' ? '免费版' : user?.plan_type}
            <Button type="link" size="small" icon={<CrownOutlined />}
              onClick={() => navigate('/pricing')}>升级套餐</Button>
          </Descriptions.Item>
        </Descriptions>
        <Button danger onClick={() => { logout(); message.success('已退出'); }}>
          退出登录
        </Button>
      </Card>
    </div>
  );
}
