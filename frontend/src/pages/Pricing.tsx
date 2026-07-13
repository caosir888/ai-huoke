import { useState, useEffect } from 'react';
import { Card, Row, Col, Button, Tag, message, Modal, Spin } from 'antd';
import { CheckCircleOutlined, CrownOutlined } from '@ant-design/icons';
import { listPlans, createOrder } from '../api/payment';
import { useAuthStore } from '../stores/authStore';

const planIcons: Record<string, React.ReactNode> = {
  free: <CheckCircleOutlined style={{ fontSize: 32, color: '#52c41a' }} />,
  basic: <CheckCircleOutlined style={{ fontSize: 32, color: '#1677ff' }} />,
  pro: <CrownOutlined style={{ fontSize: 32, color: '#fa8c16' }} />,
  enterprise: <CrownOutlined style={{ fontSize: 32, color: '#722ed1' }} />,
};

const planColors: Record<string, string> = {
  free: '#52c41a', basic: '#1677ff', pro: '#fa8c16', enterprise: '#722ed1',
};

export default function Pricing() {
  const { user } = useAuthStore();
  const [plans, setPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [subscribing, setSubscribing] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    listPlans()
      .then(res => setPlans(res.data))
      .catch(() => message.error('加载套餐失败'))
      .finally(() => setLoading(false));
  }, []);

  const handleSubscribe = async (planKey: string) => {
    if (planKey === 'free') {
      message.info('您当前已是免费版');
      return;
    }
    setSubscribing(planKey);
    try {
      const res = await createOrder(planKey);
      const order = res.data;
      Modal.info({
        title: '支付订单已生成',
        content: (
          <div>
            <p>订单号：{order.order_id}</p>
            <p>金额：¥{order.amount}</p>
            <p>套餐：{planKey}</p>
            <p style={{ color: '#999', marginTop: 8 }}>
              生产环境中将展示微信支付二维码，扫码完成支付后自动升级套餐。
            </p>
          </div>
        ),
        okText: '我知道了',
      });
    } catch {
      message.error('下单失败，请稍后重试');
    }
    setSubscribing(null);
  };

  const featureList = (plan: any) => {
    const features = [
      `每日生成${plan.daily_videos}条视频`,
      `每月生成${plan.monthly_videos || plan.daily_videos * 30}条视频`,
      `绑定${plan.accounts}个平台账号`,
      `${plan.storage_gb}GB云存储空间`,
    ];
    if (plan.key === 'pro' || plan.key === 'enterprise') {
      features.push('AI智能配音（男/女声）');
      features.push('8种混剪模板');
    }
    if (plan.key === 'enterprise') {
      features.push('专属客户经理');
      features.push('API接口对接');
    }
    return features;
  };

  return (
    <div>
      <h2>套餐与定价</h2>
      <p style={{ color: '#666', marginBottom: 24 }}>
        当前套餐：<Tag color="blue">{user?.plan_type === 'free' ? '免费版' : user?.plan_type}</Tag>
      </p>

      <Spin spinning={loading}>
        <Row gutter={[16, 16]}>
          {plans.map((plan) => {
            const isCurrent = user?.plan_type === plan.key;
            return (
              <Col xs={24} sm={12} md={6} key={plan.key}>
                <Card
                  hoverable
                  style={{
                    textAlign: 'center',
                    border: isCurrent ? `2px solid ${planColors[plan.key]}` : undefined,
                    height: '100%',
                  }}
                  title={
                    <div>
                      <div style={{ marginBottom: 8 }}>{planIcons[plan.key]}</div>
                      <div style={{ fontSize: 18 }}>{plan.name}</div>
                    </div>
                  }
                >
                  <div style={{ fontSize: 28, fontWeight: 'bold', marginBottom: 4 }}>
                    ¥{plan.price / 100}
                    <span style={{ fontSize: 14, color: '#999', fontWeight: 'normal' }}>/月</span>
                  </div>
                  <div style={{ textAlign: 'left', margin: '16px 0', color: '#666' }}>
                    {featureList(plan).map((f, i) => (
                      <div key={i} style={{ padding: '4px 0' }}>
                        <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 6 }} />
                        {f}
                      </div>
                    ))}
                  </div>
                  <Button
                    type={isCurrent ? 'default' : 'primary'}
                    block
                    disabled={isCurrent || plan.key === 'free'}
                    loading={subscribing === plan.key}
                    onClick={() => handleSubscribe(plan.key)}
                    style={{ background: !isCurrent && plan.key !== 'free' ? planColors[plan.key] : undefined }}
                  >
                    {isCurrent ? '当前套餐' : plan.price === 0 ? '免费使用' : '立即升级'}
                  </Button>
                </Card>
              </Col>
            );
          })}
        </Row>
      </Spin>
    </div>
  );
}
