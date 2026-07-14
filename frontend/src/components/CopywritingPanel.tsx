import { useState, useEffect } from 'react';
import { Card, Input, Select, Button, Tag, message, Space, Modal, Spin } from 'antd';
import { ThunderboltOutlined, LinkOutlined, CopyOutlined, StarOutlined, StarFilled } from '@ant-design/icons';
import { generateCopywriting, listCopywriting, parseLink } from '../api/content';
import { handleApiError, showSuccess } from '../utils/errorHandler';


interface Copywriting {
  id: string;
  title: string;
  body: string;
  tags: string | null;
  style: string;
  source: string;
  is_favorited: boolean;
  created_at: string;
}

export default function CopywritingPanel() {
  const [items, setItems] = useState<Copywriting[]>([]);
  const [keywords, setKeywords] = useState('');
  const [style, setStyle] = useState('口播');
  const [count, setCount] = useState(5);
  const [generating, setGenerating] = useState(false);
  const [linkUrl, setLinkUrl] = useState('');
  const [parsing, setParsing] = useState(false);
  const [parseResult, setParseResult] = useState<any>(null);
  const [parseModalOpen, setParseModalOpen] = useState(false);
  const [rewriteKeywords, setRewriteKeywords] = useState('');
  const [rewriting, setRewriting] = useState(false);
  const [loading, setLoading] = useState(false);

  const fetchList = async () => {
    setLoading(true);
    try {
      const { data } = await listCopywriting();
      setItems(data);
    } catch (err) { handleApiError(err, '加载文案失败'); }
    setLoading(false);
  };

  useEffect(() => { fetchList(); }, []);

  const handleGenerate = async () => {
    if (!keywords.trim()) { message.warning('请输入关键词'); return; }
    setGenerating(true);
    try {
      await generateCopywriting(keywords, style, count);
      showSuccess(`已生成${count}条文案`);
      await fetchList();
      setKeywords('');
    } catch (err) { handleApiError(err, '生成失败，请检查API配置'); }
    setGenerating(false);
  };

  const handleParseLink = async () => {
    if (!linkUrl.trim()) { message.warning('请输入链接'); return; }
    setParsing(true);
    try {
      const { data } = await parseLink(linkUrl);
      setParseResult(data);
      setParseModalOpen(true);
    } catch (err) { handleApiError(err, '解析失败，请检查链接'); }
    setParsing(false);
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    message.success('已复制');
  };

  const handleRewrite = async () => {
    if (!rewriteKeywords.trim()) { message.warning('请输入要仿写的产品/服务关键词'); return; }
    setRewriting(true);
    try {
      await generateCopywriting(rewriteKeywords, '口播', 3, '通用', parseResult);
      showSuccess('仿写完成，已生成3条文案');
      setParseModalOpen(false);
      setRewriteKeywords('');
      await fetchList();
    } catch (err) { handleApiError(err, '仿写失败'); }
    setRewriting(false);
  };

  return (
    <div>
      <Card title="AI文案生成" style={{ marginBottom: 24 }}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Input
            size="large" placeholder="输入行业关键词，如：重庆火锅团购、夏季防晒霜、新能源汽车..."
            value={keywords} onChange={(e) => setKeywords(e.target.value)}
            prefix="🔑"
          />
          <Space>
            <Select value={style} onChange={setStyle}
              options={[
                { label: '口播型', value: '口播' },
                { label: '展示型', value: '展示' },
                { label: '促销型', value: '促销' },
                { label: '剧情型', value: '剧情' },
              ]}
            />
            <Select value={count} onChange={setCount}
              options={[1, 3, 5, 10].map(n => ({ label: `生成${n}条`, value: n }))}
            />
            <Button type="primary" icon={<ThunderboltOutlined />}
              loading={generating} onClick={handleGenerate}>
              一键生成文案
            </Button>
          </Space>
        </Space>
      </Card>

      <Card title="爆款链接解析" style={{ marginBottom: 24 }}>
        <Space style={{ width: '100%' }}>
          <Input
            placeholder="粘贴抖音/小红书爆款视频链接"
            value={linkUrl} onChange={(e) => setLinkUrl(e.target.value)}
            prefix={<LinkOutlined />} style={{ width: 400 }}
          />
          <Button loading={parsing} onClick={handleParseLink}>解析</Button>
        </Space>
      </Card>

      <Spin spinning={loading}>
        {items.length === 0 ? (
          <div style={{ color: '#999', textAlign: 'center', padding: 40 }}>还没有文案，输入关键词生成吧</div>
        ) : (
          items.map((item) => (
            <Card key={item.id} size="small" style={{ marginBottom: 12 }}
              title={
                <Space>
                  <Tag color={item.style === '口播' ? 'blue' : item.style === '展示' ? 'green' : item.style === '促销' ? 'red' : 'purple'}>
                    {item.style}
                  </Tag>
                  <Tag color={item.source === 'ai' ? 'geekblue' : 'orange'}>{item.source === 'ai' ? 'AI生成' : '链接解析'}</Tag>
                  {item.title}
                </Space>
              }
              extra={
                <Space>
                  <Button size="small" icon={item.is_favorited ? <StarFilled /> : <StarOutlined />}>收藏</Button>
                  <Button size="small" icon={<CopyOutlined />}
                    onClick={() => handleCopy(`${item.title}\n\n${item.body}\n\n${item.tags || ''}`)}>
                    复制
                  </Button>
                </Space>
              }>
              <p style={{ whiteSpace: 'pre-wrap', marginBottom: 8 }}>{item.body}</p>
              {item.tags && <div>{item.tags.split(' ').filter(Boolean).map((t: string) => <Tag key={t}>{t}</Tag>)}</div>}
            </Card>
          ))
        )}
      </Spin>

      <Modal title="链接解析结果" open={parseModalOpen}
        onCancel={() => { setParseModalOpen(false); setRewriteKeywords(''); }}
        footer={
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Input
              placeholder="输入你的产品/服务关键词，如：成都冒烤鸭"
              value={rewriteKeywords}
              onChange={(e) => setRewriteKeywords(e.target.value)}
              style={{ width: 260 }}
            />
            <Button type="primary" loading={rewriting}
              onClick={handleRewrite} icon={<ThunderboltOutlined />}>
              仿写生成
            </Button>
          </Space>
        }>
        {parseResult && (
          <div>
            <p><strong>标题公式：</strong>{parseResult.title_formula}</p>
            <p><strong>正文结构：</strong>{parseResult.body_structure}</p>
            <p><strong>标签策略：</strong>{parseResult.tag_strategy}</p>
            <p><strong>可模仿要素：</strong>{parseResult.key_elements}</p>
          </div>
        )}
      </Modal>
    </div>
  );
}
