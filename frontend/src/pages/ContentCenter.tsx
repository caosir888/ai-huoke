import { Tabs } from 'antd';
import { EditOutlined, PictureOutlined, ScissorOutlined } from '@ant-design/icons';
import CopywritingPanel from '../components/CopywritingPanel';
import MaterialLibrary from '../components/MaterialLibrary';
import EditTaskPanel from '../components/EditTaskPanel';

export default function ContentCenter() {
  return (
    <div>
      <h2>内容中心</h2>
      <Tabs
        defaultActiveKey="copywriting"
        items={[
          { key: 'copywriting', label: <span><EditOutlined /> AI文案</span>,
            children: <CopywritingPanel /> },
          { key: 'materials', label: <span><PictureOutlined /> 素材库</span>,
            children: <MaterialLibrary /> },
          { key: 'edit', label: <span><ScissorOutlined /> 混剪任务</span>,
            children: <EditTaskPanel /> },
        ]}
      />
    </div>
  );
}
