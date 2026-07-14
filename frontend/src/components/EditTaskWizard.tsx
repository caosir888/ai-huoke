import { useState, useEffect } from 'react';
import { Modal, Steps, Card, Select, InputNumber, Radio, Button, message, Row, Col, Spin, Tag, Switch, Checkbox, Progress } from 'antd';
import { ScissorOutlined, ThunderboltOutlined } from '@ant-design/icons';
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
  { key: 'mix', name: '视频混剪', desc: '口播+产品+场景灵活组合，适合多用途内容' },
  { key: 'image_to_video', name: '图文成片', desc: '图片生成视频，支持运镜+配音+字幕' },
  { key: 'talk_show', name: '口播型', desc: '真人讲解为主，适合知识分享和口播带货' },
  { key: 'product_show', name: '产品展示型', desc: '突出产品细节和功能，适合商品推广' },
  { key: 'fast_cut', name: '卡点型', desc: '节奏感强，音乐卡点转场，适合时尚潮流内容' },
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
  const [batchMode, setBatchMode] = useState(false);
  const [batchTaskCount, setBatchTaskCount] = useState(3);
  const [selectedCopywritings, setSelectedCopywritings] = useState<string[]>([]);
  const [batchProgress, setBatchProgress] = useState(0);

  useEffect(() => {
    if (open) {
      setLoading(true);
      Promise.all([listMaterials(), listCopywriting()])
        .then(([matRes, cwRes]) => {
          setMaterials(matRes.data);
          setCopywritings(cwRes.data);
        }).catch((err) => handleApiError(err, '加载数据失败'))
        .finally(() => setLoading(false));
    }
  }, [open]);

  const handleSubmit = async () => {
    if (selectedMaterials.length < minMaterials) {
      message.warning(`请至少选择${minMaterials}段素材`);
      return;
    }
    setSubmitting(true);
    try {
      if (batchMode) {
        // Batch: randomly assign materials + copywriting for each task
        const perTaskMats = Math.max(minMaterials, Math.min(selectedMaterials.length, 6));
        const cwPool = selectedCopywritings.length > 0 ? selectedCopywritings : (selectedCopywriting ? [selectedCopywriting] : [undefined]);
        const total = batchTaskCount;
        for (let i = 0; i < total; i++) {
          setBatchProgress(Math.round((i / total) * 100));
          // Shuffle and pick
          const shuffled = [...selectedMaterials].sort(() => Math.random() - 0.5);
          const pickedMats = shuffled.slice(0, perTaskMats);
          const pickedCw = cwPool[Math.floor(Math.random() * cwPool.length)];
          await createEditTask({
            material_ids: pickedMats,
            copywriting_id: pickedCw,
            template_id: templateId,
            count: videoCount,
            duration,
            ratio,
            voice,
            subtitle_style: subtitleStyle,
          });
        }
        setBatchProgress(100);
        showSuccess(`批量创建完成：${total} 个任务`);
        onCreated();
        onClose();
        setStep(0);
        setBatchProgress(0);
      } else {
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
      }
    } catch (err) { handleApiError(err, '创建失败'); }
    setSubmitting(false);
  };

  const isImageTemplate = templateId === 'image_to_video';
  const minMaterials = batchMode ? (isImageTemplate ? 4 : 5) : (isImageTemplate ? 2 : 3);

  const steps = [
    { title: '选素材', description: batchMode ? '选择素材池（随机分配）' : (isImageTemplate ? '从素材库选择图片' : '从素材库选择视频片段') },
    { title: '选文案', description: batchMode ? '选择文案池（随机分配）' : '选择或生成视频文案' },
    { title: '设参数', description: batchMode ? '批量生成配置' : '配置剪辑模板和参数' },
  ];

  return (
    <Modal title={batchMode ? '批量创建混剪任务' : '创建剪辑任务'} open={open} onCancel={() => { onClose(); setBatchMode(false); setBatchProgress(0); }} width={700}
      footer={null} destroyOnClose>
      <Steps current={step} size="small" style={{ marginBottom: 24 }}
        items={steps.map((s, i) => ({ title: s.title, description: i === step ? s.description : undefined }))} />

      <Spin spinning={loading}>
        {/* Step 1: Select Materials */}
        {step === 0 && (
          <div>
            <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ fontWeight: 500 }}>模板类型：</span>
              <Select value={templateId} onChange={setTemplateId} style={{ width: 200 }}
                options={TEMPLATES.map(t => ({ label: t.name, value: t.key }))} />
              <span style={{ color: '#666' }}>
                已选 <strong>{selectedMaterials.length}</strong> 段素材（至少{minMaterials}段
                {batchMode && `，每任务随机取 ${Math.max(minMaterials, Math.min(selectedMaterials.length || minMaterials, 6))} 段`}）
              </span>
            </div>
            {(() => {
              const materialType = templateId === 'image_to_video' ? 'image' : 'video';
              const filteredMaterials = materials.filter(m => m.type === materialType);
              const isImage = materialType === 'image';
              return filteredMaterials.length === 0 ? (
                <div style={{ width: '100%', textAlign: 'center', color: '#999', padding: 40 }}>
                  <p style={{ fontSize: 14, marginBottom: 12 }}>
                    {isImage ? '暂无可用的图片素材' : '暂无可用的视频素材'}
                  </p>
                  <p style={{ fontSize: 12 }}>
                    {isImage
                      ? '请在「素材库」中上传 JPG/PNG 格式的图片文件，然后再来创建图文成片任务。'
                      : '请在「素材库」中上传 MP4/MOV/AVI 格式的视频文件（至少3段），然后再来创建混剪任务。'}
                  </p>
                </div>
              ) : (
                <Row gutter={[12, 12]}>
                  {filteredMaterials.map(m => (
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
                        {isImage ? (
                          <img src={m.file_url.startsWith('http') ? m.file_url : ('http://localhost:8000' + m.file_url)}
                            style={{ width: '100%', height: 100, objectFit: 'cover', borderRadius: 4 }} alt={m.file_name} />
                        ) : (
                          <video src={m.file_url.startsWith('http') ? m.file_url : ('http://localhost:8000' + m.file_url)}
                            style={{ width: '100%', height: 100, objectFit: 'cover', borderRadius: 4 }} />
                        )}
                        <div style={{ marginTop: 4, fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {m.file_name}
                        </div>
                        <Tag style={{ fontSize: 10 }} color={isImage ? 'green' : 'blue'}>
                          {isImage ? '图片' : '视频'}
                        </Tag>
                        <span style={{ fontSize: 11, color: '#999' }}>{m.duration ? `${m.duration.toFixed(1)}s` : ''}</span>
                      </Card>
                    </Col>
                  ))}
                </Row>
              );
            })()}
          </div>
        )}

        {/* Step 2: Select Copywriting */}
        {step === 1 && (
          <div>
            <p style={{ color: '#666', marginBottom: 12 }}>
              {batchMode
                ? `选择文案池（每个任务随机选一条）：已选 ${selectedCopywritings.length} 条`
                : '选择用于视频配音的文案（可选）'}
            </p>
            {copywritings.length === 0 ? (
              <div style={{ textAlign: 'center', color: '#999', padding: 40 }}>
                暂无可用的文案，请先在AI文案中生成
              </div>
            ) : batchMode ? (
              <Checkbox.Group value={selectedCopywritings} onChange={v => setSelectedCopywritings(v as string[])} style={{ width: '100%' }}>
                {copywritings.map(cw => (
                  <Card key={cw.id} size="small" hoverable
                    style={{ marginBottom: 8, border: selectedCopywritings.includes(cw.id) ? '2px solid #1677ff' : undefined }}>
                    <Checkbox value={cw.id}>
                      <strong>{cw.title}</strong>
                      <span style={{ color: '#999', marginLeft: 8 }}>{cw.style}</span>
                    </Checkbox>
                  </Card>
                ))}
              </Checkbox.Group>
            ) : (
              <Radio.Group style={{ width: '100%' }} value={selectedCopywriting}
                onChange={e => setSelectedCopywriting(e.target.value)}>
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
                <Select value={voice} onChange={setVoice} style={{ width: '100%' }}
                  options={[
                    { label: '无配音', value: 'none' },
                    { label: '━━ 真人女声 ━━', value: '_div_f', disabled: true },
                    { label: '温暖女声 — 带货种草', value: 'female_warm' },
                    { label: '甜美女声 — 美妆护肤', value: 'female_sweet' },
                    { label: '新闻女声 — 快节奏口播', value: 'female_news' },
                    { label: '故事女声 — 沉浸叙事', value: 'female_story' },
                    { label: '温柔女声 — 生活方式', value: 'female_gentle' },
                    { label: '活泼女声 — 潮流娱乐', value: 'female_lively' },
                    { label: '台湾女声 — 清新文艺', value: 'female_tw' },
                    { label: '台湾甜美女声', value: 'female_tw_sweet' },
                    { label: '━━ 真人男声 ━━', value: '_div_m', disabled: true },
                    { label: '专业男声 — 知识讲解', value: 'male_professional' },
                    { label: '深沉男声 — 品牌宣传', value: 'male_deep' },
                    { label: '阳光男声 — 日常Vlog', value: 'male_sunshine' },
                    { label: '激情男声 — 运动促销', value: 'male_passion' },
                    { label: '休闲男声 — 随性分享', value: 'male_casual' },
                    { label: '台湾男声 — 温暖治愈', value: 'male_tw' },
                    { label: '━━ 方言特色 ━━', value: '_div_d', disabled: true },
                    { label: '东北话 — 幽默搞笑', value: 'dialect_liaoning' },
                    { label: '陕西话 — 豪迈直爽', value: 'dialect_shaanxi' },
                  ]} />
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
              <Col span={24}>
                <Card size="small" style={{ background: '#fafafa' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                      <span style={{ fontWeight: 500, marginRight: 8 }}>批量模式</span>
                      <Switch checked={batchMode} onChange={setBatchMode} />
                      <span style={{ color: '#999', marginLeft: 8, fontSize: 12 }}>
                        自动从素材池和文案池中随机组合，一次创建多个任务
                      </span>
                    </div>
                    {batchMode && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <label>任务数</label>
                        <InputNumber min={2} max={20} value={batchTaskCount}
                          onChange={v => setBatchTaskCount(v || 3)} style={{ width: 70 }} />
                      </div>
                    )}
                  </div>
                </Card>
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
            <Button type="primary" icon={batchMode ? <ThunderboltOutlined /> : <ScissorOutlined />}
              loading={submitting} onClick={handleSubmit}>
              {batchMode ? `批量生成 ${batchTaskCount} 个任务` : '开始混剪'}
            </Button>
          )}
          {batchMode && submitting && batchProgress > 0 && (
            <div style={{ marginTop: 8 }}>
              <Progress percent={batchProgress} size="small" />
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
