import { useState, useEffect } from 'react';
import { Modal, Steps, Card, Select, InputNumber, Radio, Button, message, Row, Col, Spin } from 'antd';
import { ScissorOutlined } from '@ant-design/icons';
import { listMaterials, createEditTask, listCopywriting } from '../api/content';
import { handleApiError, showSuccess } from '../utils/errorHandler';

interface Material {
  id: string;
  file_name: string;
  type: string;
  file_url: string;
  duration: number | null;
}

interface Copywriting {
  id: string;
  title: string;
  style: string;
}

const TEMPLATES = [
  { key: 'talk_show', name: '口播型', desc: '真人讲解为主，适合知识分享和口播带货' },
  { key: 'product_show', name: '产品展示型', desc: '突出产品细节和功能，适合商品推广' },
  { key: 'fast_cut', name: '卡点型', desc: '节奏感强，音乐卡点转场，适合时尚潮流内容' },
  { key: 'mix', name: '混搭型', desc: '口播+产品+场景灵活组合，适合多用途内容' },
  { key: 'flash', name: '快闪型', desc: '信息密度高，快速切换画面，适合促销和活动预告' },
  { key: 'before_after', name: '前后对比型', desc: '改造前后/使用前后对比，适合装修、美业等行业' },
  { key: 'tutorial', name: '教程型', desc: '步骤清晰的教程结构，适合教学、DIY、美食教程' },
  { key: 'review', name: '测评型', desc: '开箱→测评→评价，适合3C数码、美妆测评等内容' },
];

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export default function EditTaskWizard({ open, onClose, onCreated }: Props) {
  const [step, setStep] = useState(0);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [selectedMaterials, setSelectedMaterials] = useState<string[]>([]);
  const [copywritings, setCopywritings] = useState<Copywriting[]>([]);
  const [selectedCopywriting, setSelectedCopywriting] = useState<string | undefined>();
  const [templateId, setTemplateId] = useState('mix');
  const [videoCount, setVideoCount] = useState(5);
  const [duration, setDuration] = useState(30);
  const [ratio, setRatio] = useState('9:16');
  const [voice, setVoice] = useState('none');
  const [subtitleStyle, setSubtitleStyle] = useState('white_black_border');
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      setLoading(true);
      Promise.all([listMaterials({ type: 'video' }), listCopywriting()])
        .then(([matRes, cwRes]) => {
          setMaterials(matRes.data);
          setCopywritings(cwRes.data);
        }).catch((err) => handleApiError(err, '加载数据失败'))
        .finally(() => setLoading(false));
    }
  }, [open]);

  const handleSubmit = async () => {
    if (selectedMaterials.length < 3) {
      message.warning('请至少选择3段素材');
      return;
    }
    setSubmitting(true);
    try {
      await createEditTask({
        material_ids: selectedMaterials,
        copywriting_id: selectedCopywriting,
        template_id: templateId,
        count: videoCount,
        duration,
        ratio,
        voice,
        subtitle_style: subtitleStyle,
      });
      showSuccess('剪辑任务已创建，正在排队处理');
      onCreated();
      onClose();
      setStep(0);
    } catch (err) { handleApiError(err, '创建失败'); }
    setSubmitting(false);
  };

  const steps = [
    { title: '选素材', description: '从素材库选择视频片段' },
    { title: '选文案', description: '选择或生成视频文案' },
    { title: '设参数', description: '配置剪辑模板和参数' },
  ];

  return (
    <Modal title="创建剪辑任务" open={open} onCancel={onClose} width={700}
      footer={null} destroyOnClose>
      <Steps current={step} size="small" style={{ marginBottom: 24 }}
        items={steps.map((s, i) => ({ title: s.title, description: i === step ? s.description : undefined }))} />

      <Spin spinning={loading}>
        {/* Step 1: Select Materials */}
        {step === 0 && (
          <div>
            <p style={{ marginBottom: 12, color: '#666' }}>已选 <strong>{selectedMaterials.length}</strong> 段素材（至少3段）</p>
            <Row gutter={[12, 12]}>
              {materials.filter(m => m.type === 'video').map(m => (
                <Col span={8} key={m.id}>
                  <Card
                    size="small"
                    hoverable
                    style={{ border: selectedMaterials.includes(m.id) ? '2px solid #1677ff' : undefined }}
                    onClick={() => {
                      setSelectedMaterials(prev =>
                        prev.includes(m.id) ? prev.filter(id => id !== m.id) : [...prev, m.id]
                      );
                    }}
                  >
                    <video src={m.file_url.startsWith('http') ? m.file_url : ('http://localhost:8000' + m.file_url)} style={{ width: '100%', height: 100, objectFit: 'cover', borderRadius: 4 }} />
                    <div style={{ marginTop: 4, fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {m.file_name}
                    </div>
                    <span style={{ fontSize: 11, color: '#999' }}>{m.duration ? `${m.duration.toFixed(1)}s` : ''}</span>
                  </Card>
                </Col>
              ))}
              {materials.filter(m => m.type === 'video').length === 0 && (
                <div style={{ width: '100%', textAlign: 'center', color: '#999', padding: 40 }}>
                  <p style={{ fontSize: 14, marginBottom: 12 }}>暂无可用的视频素材</p>
                  <p style={{ fontSize: 12 }}>请在「素材库」中上传 MP4/MOV/AVI 格式的视频文件（至少3段），然后再来创建混剪任务。</p>
                  <p style={{ fontSize: 12, color: '#fa8c16' }}>注意：图片文件不适用于视频混剪，请上传视频素材。</p>
                </div>
              )}
            </Row>
          </div>
        )}

        {/* Step 2: Select Copywriting */}
        {step === 1 && (
          <div>
            <p style={{ color: '#666', marginBottom: 12 }}>选择用于视频配音的文案（可选）</p>
            <Radio.Group
              style={{ width: '100%' }}
              value={selectedCopywriting}
              onChange={e => setSelectedCopywriting(e.target.value)}
            >
              {copywritings.map(cw => (
                <Card key={cw.id} size="small" hoverable
                  style={{ marginBottom: 8, border: selectedCopywriting === cw.id ? '2px solid #1677ff' : undefined }}>
                  <Radio value={cw.id}>
                    <strong>{cw.title}</strong>
                    <span style={{ color: '#999', marginLeft: 8 }}>{cw.style}</span>
                  </Radio>
                </Card>
              ))}
            </Radio.Group>
            {copywritings.length === 0 && (
              <div style={{ textAlign: 'center', color: '#999', padding: 40 }}>
                暂无可用的文案，请先在AI文案中生成
              </div>
            )}
          </div>
        )}

        {/* Step 3: Parameters */}
        {step === 2 && (
          <div>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <label>混剪模板</label>
                <Select value={templateId} onChange={setTemplateId} style={{ width: '100%' }}
                  options={TEMPLATES.map(t => ({ label: t.name, value: t.key }))} />
              </Col>
              <Col span={12}>
                <label>生成数量</label>
                <InputNumber min={1} max={50} value={videoCount} onChange={v => setVideoCount(v || 5)} style={{ width: '100%' }} />
              </Col>
              <Col span={12}>
                <label>视频时长(秒)</label>
                <InputNumber min={15} max={120} step={5} value={duration}
                  onChange={v => setDuration(v || 30)} style={{ width: '100%' }} />
              </Col>
              <Col span={12}>
                <label>画面比例</label>
                <Radio.Group value={ratio} onChange={e => setRatio(e.target.value)}>
                  <Radio.Button value="9:16">9:16 抖音</Radio.Button>
                  <Radio.Button value="16:9">16:9 横屏</Radio.Button>
                  <Radio.Button value="1:1">1:1 方形</Radio.Button>
                </Radio.Group>
              </Col>
              <Col span={12}>
                <label>AI配音</label>
                <Radio.Group value={voice} onChange={e => setVoice(e.target.value)}>
                  <Radio.Button value="none">无配音</Radio.Button>
                  <Radio.Button value="female">女声</Radio.Button>
                  <Radio.Button value="male">男声</Radio.Button>
                </Radio.Group>
              </Col>
              <Col span={12}>
                <label>字幕样式</label>
                <Select value={subtitleStyle} onChange={setSubtitleStyle}
                  options={[
                    { label: '白字黑边', value: 'white_black_border' },
                    { label: '黄字黑边', value: 'yellow_black_border' },
                    { label: '黑字白边', value: 'black_white_border' },
                  ]} />
              </Col>
            </Row>
          </div>
        )}
      </Spin>

      {/* Footer buttons */}
      <div style={{ marginTop: 24, display: 'flex', justifyContent: 'space-between' }}>
        <div>
          {step > 0 && <Button onClick={() => setStep(step - 1)}>上一步</Button>}
        </div>
        <div>
          <Button onClick={onClose} style={{ marginRight: 8 }}>取消</Button>
          {step < 2 ? (
            <Button type="primary" onClick={() => setStep(step + 1)}>下一步</Button>
          ) : (
            <Button type="primary" icon={<ScissorOutlined />}
              loading={submitting} onClick={handleSubmit}>
              开始混剪
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
