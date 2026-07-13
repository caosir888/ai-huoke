import { useState } from 'react';
import { Modal, Card, Row, Col, Button, message } from 'antd';
import {
  ShopOutlined, CoffeeOutlined, CarOutlined, SkinOutlined,
  HomeOutlined, MedicineBoxOutlined, BookOutlined, AppstoreOutlined,
} from '@ant-design/icons';
import { updateProfile } from '../api/auth';
import { useAuthStore } from '../stores/authStore';

const INDUSTRIES = [
  { key: '餐饮', name: '餐饮美食', icon: <CoffeeOutlined />, color: '#f50', desc: '火锅、烧烤、奶茶、小吃等' },
  { key: '美业', name: '美容美业', icon: <SkinOutlined />, color: '#eb2f96', desc: '美发、美甲、医美、SPA等' },
  { key: '汽车', name: '汽车服务', icon: <CarOutlined />, color: '#1677ff', desc: '4S店、二手车、维修保养等' },
  { key: '零售', name: '零售门店', icon: <ShopOutlined />, color: '#52c41a', desc: '服装、超市、便利店等' },
  { key: '家居', name: '家居装修', icon: <HomeOutlined />, color: '#fa8c16', desc: '装修公司、建材、家具等' },
  { key: '教育', name: '教育培训', icon: <BookOutlined />, color: '#2f54eb', desc: 'K12、兴趣班、职业培训等' },
  { key: '医疗', name: '医疗健康', icon: <MedicineBoxOutlined />, color: '#13c2c2', desc: '诊所、牙科、体检中心等' },
  { key: '其他', name: '其他行业', icon: <AppstoreOutlined />, color: '#8c8c8c', desc: '以上都不是' },
];

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function IndustrySelector({ open, onClose }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const { fetchUser } = useAuthStore();

  const handleConfirm = async () => {
    if (!selected) {
      message.warning('请选择一个行业');
      return;
    }
    setSaving(true);
    try {
      await updateProfile({ industry: selected });
      await fetchUser();
      message.success(`已选择「${selected}」行业，AI将为您推荐相关文案模板`);
      onClose();
    } catch {
      message.error('保存失败');
    }
    setSaving(false);
  };

  return (
    <Modal
      title="选择你的行业，让我们为你定制内容"
      open={open}
      closable={false}
      footer={null}
      width={640}
      centered
    >
      <p style={{ color: '#666', marginBottom: 16 }}>
        选择后AI文案将优先推荐你所在行业的爆款模板和话题标签
      </p>
      <Row gutter={[12, 12]}>
        {INDUSTRIES.map((ind) => (
          <Col span={6} key={ind.key}>
            <Card
              hoverable
              size="small"
              style={{
                textAlign: 'center',
                cursor: 'pointer',
                border: selected === ind.key ? `2px solid ${ind.color}` : undefined,
              }}
              onClick={() => setSelected(ind.key)}
            >
              <div style={{ fontSize: 28, color: ind.color, marginBottom: 4 }}>
                {ind.icon}
              </div>
              <div style={{ fontWeight: 500, fontSize: 13 }}>{ind.name}</div>
              <div style={{ fontSize: 11, color: '#999' }}>{ind.desc}</div>
            </Card>
          </Col>
        ))}
      </Row>
      <div style={{ marginTop: 16, textAlign: 'center' }}>
        <Button type="primary" size="large" onClick={handleConfirm}
          loading={saving} disabled={!selected}>
          确认选择
        </Button>
        <Button type="link" onClick={onClose} style={{ marginLeft: 8 }}>
          跳过，使用通用模板
        </Button>
      </div>
    </Modal>
  );
}
