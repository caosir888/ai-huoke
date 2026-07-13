import { Empty, Button } from 'antd';
import { useNavigate } from 'react-router-dom';

interface Props {
  description?: string;
  actionText?: string;
  actionPath?: string;
  onAction?: () => void;
}

export default function EmptyState({
  description = '暂无数据',
  actionText,
  actionPath,
  onAction,
}: Props) {
  const navigate = useNavigate();

  const handleClick = () => {
    if (onAction) onAction();
    else if (actionPath) navigate(actionPath);
  };

  return (
    <Empty
      description={description}
      style={{ padding: '60px 0' }}
    >
      {actionText && (
        <Button type="primary" onClick={handleClick}>
          {actionText}
        </Button>
      )}
    </Empty>
  );
}
