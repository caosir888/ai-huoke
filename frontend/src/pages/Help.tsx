import { Card, Collapse, Typography, Steps, Tag } from 'antd';
import { QuestionCircleOutlined, BookOutlined, VideoCameraOutlined, ThunderboltOutlined } from '@ant-design/icons';

const { Title, Paragraph, Text } = Typography;

const faqItems = [
  {
    key: 'q1',
    label: '如何生成第一条AI文案？',
    children: (
      <div>
        <Paragraph>在「内容中心 → AI文案」输入行业关键词（如"重庆火锅"），选择风格，点击"一键生成文案"即可。</Paragraph>
        <Paragraph><Text strong>提示：</Text>关键词越具体，生成的文案越精准。建议包含行业词+场景词，如"夏季防晒霜推荐"比"护肤品"效果好。</Paragraph>
      </div>
    ),
  },
  {
    key: 'q2',
    label: '混剪需要多少段素材？最少需要什么？',
    children: (
      <div>
        <Paragraph>最少需要 <Tag>3段</Tag> 视频素材。建议准备5-10段不同角度/场景的素材，AI会自动剪辑出不重复的成品。</Paragraph>
        <Paragraph>支持的格式：MP4、MOV、AVI。单文件最大500MB。推荐1080P竖屏（9:16）拍摄。</Paragraph>
      </div>
    ),
  },
  {
    key: 'q3',
    label: '免费版和付费版有什么区别？',
    children: (
      <div>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f5f5f5' }}>
              <th style={{ padding: 8, border: '1px solid #e8e8e8' }}>功能</th>
              <th style={{ padding: 8, border: '1px solid #e8e8e8' }}>免费版</th>
              <th style={{ padding: 8, border: '1px solid #e8e8e8' }}>基础版 ¥99/月</th>
              <th style={{ padding: 8, border: '1px solid #e8e8e8' }}>专业版 ¥299/月</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style={{ padding: 8, border: '1px solid #e8e8e8' }}>每日视频</td>
              <td style={{ padding: 8, border: '1px solid #e8e8e8' }}>3条</td>
              <td style={{ padding: 8, border: '1px solid #e8e8e8' }}>10条</td>
              <td style={{ padding: 8, border: '1px solid #e8e8e8' }}>50条</td>
            </tr>
            <tr>
              <td style={{ padding: 8, border: '1px solid #e8e8e8' }}>绑定账号</td>
              <td style={{ padding: 8, border: '1px solid #e8e8e8' }}>1个</td>
              <td style={{ padding: 8, border: '1px solid #e8e8e8' }}>5个</td>
              <td style={{ padding: 8, border: '1px solid #e8e8e8' }}>20个</td>
            </tr>
            <tr>
              <td style={{ padding: 8, border: '1px solid #e8e8e8' }}>云存储</td>
              <td style={{ padding: 8, border: '1px solid #e8e8e8' }}>1GB</td>
              <td style={{ padding: 8, border: '1px solid #e8e8e8' }}>10GB</td>
              <td style={{ padding: 8, border: '1px solid #e8e8e8' }}>50GB</td>
            </tr>
            <tr>
              <td style={{ padding: 8, border: '1px solid #e8e8e8' }}>AI配音</td>
              <td style={{ padding: 8, border: '1px solid #e8e8e8' }}>-</td>
              <td style={{ padding: 8, border: '1px solid #e8e8e8' }}>✓</td>
              <td style={{ padding: 8, border: '1px solid #e8e8e8' }}>✓</td>
            </tr>
          </tbody>
        </table>
      </div>
    ),
  },
  {
    key: 'q4',
    label: '发布到抖音需要什么条件？',
    children: (
      <div>
        <Paragraph>需在「账号管理」绑定抖音账号。当前支持两种发布方式：</Paragraph>
        <ol>
          <li><Text strong>API发布：</Text>需抖音企业认证，通过开放平台授权绑定</li>
          <li><Text strong>RPA模拟发布：</Text>作为备选方案，自动模拟浏览器操作完成发布</li>
        </ol>
        <Paragraph>未来将支持快手、小红书、视频号等多平台一键分发。</Paragraph>
      </div>
    ),
  },
  {
    key: 'q5',
    label: '生成的视频会有重复吗？',
    children: (
      <div>
        <Paragraph>系统会自动对生成的视频进行去重检测。即使使用相同素材，AI也会：</Paragraph>
        <ul>
          <li>随机选取不同的素材片段组合</li>
          <li>调整每段素材的裁剪起止点</li>
          <li>应用不同的转场效果</li>
          <li>通过帧采样哈希比对确保去重率&lt;30%</li>
        </ul>
        <Paragraph>确保每次生成的视频都是不重复的原创内容。</Paragraph>
      </div>
    ),
  },
  {
    key: 'q6',
    label: '数据什么时候更新？',
    children: (
      <div>
        <Paragraph>视频发布后的播放量、点赞等数据，系统每小时自动拉取一次。也可以在发布管理页面点击刷新手动获取最新数据。</Paragraph>
        <Paragraph>V2.0将支持实时数据看板和全链路获客漏斗分析。</Paragraph>
      </div>
    ),
  },
];

const quickStartSteps = [
  { title: '注册登录', description: '手机号注册，选择你的行业' },
  { title: '生成文案', description: '输入关键词，AI自动生成爆款文案' },
  { title: '上传素材', description: '上传拍摄的视频/图片素材' },
  { title: '创建混剪', description: '选择素材和文案，一键生成多条视频' },
  { title: '发布视频', description: '绑定平台账号，发布到抖音等平台' },
];

export default function Help() {
  return (
    <div style={{ maxWidth: 800 }}>
      <Title level={3}><BookOutlined /> 帮助中心</Title>

      <Card title={<span><ThunderboltOutlined /> 快速上手（5步）</span>} style={{ marginBottom: 24 }}>
        <Steps
          direction="vertical"
          size="small"
          current={-1}
          items={quickStartSteps.map((s) => ({
            title: s.title,
            description: s.description,
          }))}
        />
      </Card>

      <Card title={<span><QuestionCircleOutlined /> 常见问题</span>}>
        <Collapse items={faqItems} />
      </Card>

      <Card title={<span><VideoCameraOutlined /> 视频教程</span>} style={{ marginTop: 24 }}>
        <Paragraph>
          更详细的视频教程请关注我们的官方抖音号/视频号，搜索「AI获客」即可找到。
        </Paragraph>
        <Paragraph style={{ color: '#999' }}>
          或在微信搜索小程序「AI获客帮助」获取图文教程和最新更新公告。
        </Paragraph>
      </Card>
    </div>
  );
}
