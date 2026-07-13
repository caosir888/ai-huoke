import { useState } from 'react';
import { Button, Modal, Input, Rate, message } from 'antd';
import { MessageOutlined } from '@ant-design/icons';
import { submitFeedback } from '../api/feedback';
import { handleApiError } from '../utils/errorHandler';

export default function FeedbackButton() {
  const [open, setOpen] = useState(false);
  const [rating, setRating] = useState(0);
  const [content, setContent] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!content.trim()) {
      message.warning('请填写反馈内容');
      return;
    }
    setSubmitting(true);
    try {
      await submitFeedback(rating, content);
      message.success('感谢您的反馈！我们会认真评估改进');
      setOpen(false);
      setRating(0);
      setContent('');
    } catch (err) {
      handleApiError(err, '提交失败，请稍后重试');
    }
    setSubmitting(false);
  };

  return (
    <>
      <Button
        type="primary"
        shape="circle"
        size="large"
        icon={<MessageOutlined />}
        onClick={() => setOpen(true)}
        style={{
          position: 'fixed',
          bottom: 40,
          right: 40,
          zIndex: 1000,
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        }}
      />
      <Modal
        title="反馈建议"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={handleSubmit}
        confirmLoading={submitting}
        okText="提交反馈"
      >
        <div style={{ marginBottom: 16 }}>
          <p style={{ marginBottom: 8 }}>整体评分</p>
          <Rate value={rating} onChange={setRating} />
        </div>
        <div>
          <p style={{ marginBottom: 8 }}>使用感受或建议</p>
          <Input.TextArea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={4}
            maxLength={500}
            placeholder="请告诉我们你的使用体验、遇到的问题或希望新增的功能..."
          />
        </div>
      </Modal>
    </>
  );
}
