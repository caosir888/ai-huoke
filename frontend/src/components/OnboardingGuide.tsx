import { useState } from 'react';
import { Modal, Steps, Button, Card, Typography } from 'antd';
import { ThunderboltOutlined, UploadOutlined, ScissorOutlined, SendOutlined } from '@ant-design/icons';



const { Title, Paragraph } = Typography;

const steps = [
  {
    title: '生成文案',
    icon: <ThunderboltOutlined />,
    content: '在「内容中心 → AI文案」输入行业关键词（如"重庆火锅"），AI自动生成多条爆款短视频文案。也可以粘贴同行爆款链接，一键拆解仿写。',
    action: { label: '去生成文案', path: '/content' },
  },
  {
    title: '上传素材',
    icon: <UploadOutlined />,
    content: '在「内容中心 → 素材库」上传你拍摄的视频/图片素材。支持拖拽批量上传，自动云端保存。按产品展示、门店环境、客户案例等分类管理。',
    action: { label: '去上传素材', path: '/content?tab=materials' },
  },
  {
    title: '创建混剪',
    icon: <ScissorOutlined />,
    content: '选好素材和文案后，在「内容中心 → 混剪任务」点击"创建剪辑任务"，按3步向导选择素材→选择文案→设置参数（模板/数量/时长/配音），AI自动批量生成多条不重复的高质量视频。',
    action: { label: '去创建混剪', path: '/content?tab=edit' },
  },
  {
    title: '发布到平台',
    icon: <SendOutlined />,
    content: '混剪完成后，在「发布管理」选择视频→选择绑定的平台账号→填写标题→一键发布到抖音/快手/小红书/视频号。支持立即发布和定时发布。',
    action: { label: '去发布视频', path: '/publish' },
  },
];

export default function OnboardingGuide({ visible, onClose }: { visible: boolean; onClose: () => void }) {
  const [current, setCurrent] = useState(0);

  const handleClose = () => {
    localStorage.setItem('onboarding_done', 'true');
    onClose();
  };

  const handleNext = () => {
    if (current < steps.length - 1) {
      setCurrent(current + 1);
    } else {
      handleClose();
    }
  };

  const currentStep = steps[current];

  return (
    <Modal
      open={visible}
      closable={false}
      footer={null}
      width={680}
      centered
    >
      <Title level={4} style={{ textAlign: 'center', marginBottom: 24 }}>
        欢迎使用 AI获客，只需4步轻松上手
      </Title>
      <Steps current={current} size="small" style={{ marginBottom: 24 }}
        items={steps.map(s => ({ title: s.title, icon: s.icon }))} />
      <Card style={{ textAlign: 'center', padding: '24px 0' }}>
        <div style={{ fontSize: 40, marginBottom: 16 }}>
          {currentStep.icon}
        </div>
        <Title level={5}>第{current + 1}步：{currentStep.title}</Title>
        <Paragraph style={{ color: '#666', maxWidth: 500, margin: '0 auto' }}>
          {currentStep.content}
        </Paragraph>
      </Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
        <Button type="text" onClick={handleClose}>
          {current === 0 ? '跳过引导' : '知道了，开始使用'}
        </Button>
        <div>
          {current > 0 && (
            <Button onClick={() => setCurrent(current - 1)} style={{ marginRight: 8 }}>
              上一步
            </Button>
          )}
          {current < steps.length - 1 ? (
            <Button type="primary" onClick={handleNext}>下一步</Button>
          ) : (
            <Button type="primary" onClick={handleClose}>开始使用</Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
