import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';

const platformNames: Record<string, string> = {
  douyin: '抖音', kuaishou: '快手', xhs: '小红书', shipinhao: '视频号',
};

export default function OAuthCallback() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const bindStatus = searchParams.get('bind_status');
    const platform = searchParams.get('platform') || 'douyin';
    const error = searchParams.get('error');
    const whitelist = searchParams.get('whitelist');

    if (bindStatus === 'success') {
      setStatus('success');
      if (whitelist === '1') {
        setMessage('抖音测试白名单已加入成功！现在可以返回应用进行正式授权了');
      } else {
        setMessage(`${platformNames[platform] || platform}账号授权成功`);
      }
      if (window.opener) {
        window.opener.postMessage({ type: 'oauth_callback', status: 'success', platform, whitelist: whitelist === '1' }, window.location.origin);
      }
    } else if (error) {
      setStatus('error');
      setMessage(decodeURIComponent(error));
      if (window.opener) {
        window.opener.postMessage({ type: 'oauth_callback', status: 'error', error: decodeURIComponent(error) }, window.location.origin);
      }
    } else {
      setStatus('error');
      setMessage('无效的回调参数');
    }

    // Auto-close the popup after a short delay (only for popup windows)
    const timer = setTimeout(() => {
      if (window.opener) {
        window.close();
      }
    }, 3000);

    return () => clearTimeout(timer);
  }, [searchParams]);

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      height: '100vh', fontFamily: 'system-ui, sans-serif', gap: 16,
    }}>
      {status === 'loading' && <div style={{ fontSize: 18, color: '#666' }}>正在处理授权...</div>}
      {status === 'success' && (
        <>
          <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} />
          <div style={{ fontSize: 18, fontWeight: 600 }}>{message}</div>
          <div style={{ color: '#999', fontSize: 14 }}>窗口即将关闭，请返回原页面查看</div>
        </>
      )}
      {status === 'error' && (
        <>
          <CloseCircleOutlined style={{ fontSize: 48, color: '#ff4d4f' }} />
          <div style={{ fontSize: 18, fontWeight: 600 }}>授权失败</div>
          <div style={{ color: '#999', fontSize: 14 }}>{message}</div>
        </>
      )}
    </div>
  );
}
