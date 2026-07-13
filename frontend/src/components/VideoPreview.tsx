import { useState, useRef } from 'react';
import { Modal, Button, Space, message, Spin } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';

interface Props {
  url: string | null;
  visible: boolean;
  onClose: () => void;
}

export default function VideoPreview({ url, visible, onClose }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [loading, setLoading] = useState(true);

  const handleDownload = () => {
    if (url) {
      const a = document.createElement('a');
      a.href = url;
      a.download = 'video.mp4';
      a.click();
      message.success('开始下载');
    }
  };

  return (
    <Modal
      title="视频预览"
      open={visible}
      onCancel={onClose}
      width={480}
      footer={
        <Space>
          <Button icon={<DownloadOutlined />} onClick={handleDownload}>下载</Button>
          <Button onClick={onClose}>关闭</Button>
        </Space>
      }
      destroyOnClose
    >
      {loading && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
          <Spin tip="加载视频..." />
        </div>
      )}
      {url ? (
        <video
          ref={videoRef}
          src={url}
          controls
          autoPlay
          style={{ width: '100%', maxHeight: '70vh', borderRadius: 8, display: loading ? 'none' : 'block' }}
          onLoadedData={() => setLoading(false)}
          onError={() => { setLoading(false); message.error('视频加载失败'); }}
        />
      ) : (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>视频不可用</div>
      )}
    </Modal>
  );
}
