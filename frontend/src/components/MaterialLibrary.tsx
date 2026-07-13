import { useState, useEffect } from 'react';
import { Card, Upload, Button, Tree, Table, Tag, Popconfirm, Modal, Input } from 'antd';
import { FolderAddOutlined, DeleteOutlined, InboxOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { listMaterials, listFolders, createFolder, deleteMaterial, uploadMaterial } from '../api/content';
import { handleApiError, showSuccess } from '../utils/errorHandler';

const { Dragger } = Upload;

interface Material {
  id: string;
  type: string;
  file_name: string;
  file_url: string;
  thumbnail_url: string | null;
  duration: number | null;
  size: number;
  tags: string[];
  created_at: string;
}

interface Folder {
  id: string;
  name: string;
  parent_id: string | null;
}

function formatSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function MaterialLibrary() {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [folderModalOpen, setFolderModalOpen] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [matRes, folRes] = await Promise.all([listMaterials({ folder_id: selectedFolder || undefined }), listFolders()]);
      setMaterials(matRes.data);
      setFolders(folRes.data);
    } catch (err) { handleApiError(err, '加载素材失败'); }
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, [selectedFolder]);

  const handleUpload = async (file: File) => {
    try {
      const fd = new FormData();
      fd.append('file', file);
      if (selectedFolder) fd.append('folder_id', selectedFolder);
      await uploadMaterial(fd);
      showSuccess(`上传成功: ${file.name}`);
      await fetchData();
    } catch (err) { handleApiError(err, '上传失败'); }
    return false;
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;
    try {
      await createFolder(newFolderName, selectedFolder || undefined);
      showSuccess('分类已创建');
      setFolderModalOpen(false);
      setNewFolderName('');
      await fetchData();
    } catch (err) { handleApiError(err, '创建失败'); }
  };

  const treeData = [
    { title: '全部素材', key: '__all__', isLeaf: true },
    ...folders.map(f => ({ title: f.name, key: f.id, isLeaf: true })),
  ];

  const columns: ColumnsType<Material> = [
    { title: '文件名', dataIndex: 'file_name', key: 'file_name', ellipsis: true },
    { title: '类型', dataIndex: 'type', key: 'type', width: 80,
      render: (t: string) => <Tag color={t === 'video' ? 'blue' : 'green'}>{t === 'video' ? '视频' : '图片'}</Tag> },
    { title: '大小', dataIndex: 'size', key: 'size', width: 100, render: (s: number) => formatSize(s) },
    { title: '时长', dataIndex: 'duration', key: 'duration', width: 80,
      render: (d: number | null) => d ? `${d.toFixed(1)}s` : '-' },
    { title: '标签', dataIndex: 'tags', key: 'tags',
      render: (tags: string[]) => tags?.map(t => <Tag key={t}>{t}</Tag>) },
    { title: '上传时间', dataIndex: 'created_at', key: 'created_at', width: 160,
      render: (d: string) => new Date(d).toLocaleString() },
    { title: '操作', key: 'action', width: 80, render: (_, record) => (
      <Popconfirm title="确定删除？" onConfirm={async () => { await deleteMaterial(record.id); fetchData(); }}>
        <Button size="small" danger icon={<DeleteOutlined />} />
      </Popconfirm>
    )},
  ];

  return (
    <div>
      <Card title="素材库" style={{ marginBottom: 24 }}>
        <Dragger
          multiple
          showUploadList={false}
          beforeUpload={handleUpload}
          accept="video/*,image/*,audio/*"
        >
          <p className="ant-upload-drag-icon"><InboxOutlined /></p>
          <p>点击或拖拽文件到此区域上传</p>
          <p style={{ color: '#999' }}>支持 MP4/MOV/AVI/JPG/PNG/MP3 格式，单文件最大 500MB</p>
        </Dragger>
      </Card>

      <div style={{ display: 'flex', gap: 24 }}>
        <Card title="分类" style={{ width: 220 }}>
          <Tree
            treeData={treeData}
            defaultExpandAll
            selectedKeys={selectedFolder ? [selectedFolder] : ['__all__']}
            onSelect={(keys) => setSelectedFolder(keys[0] === '__all__' ? null : keys[0] as string)}
          />
          <Button type="dashed" icon={<FolderAddOutlined />} block
            style={{ marginTop: 12 }}
            onClick={() => setFolderModalOpen(true)}>
            新建分类
          </Button>
        </Card>

        <div style={{ flex: 1 }}>
          <Table
            columns={columns}
            dataSource={materials}
            rowKey="id"
            loading={loading}
            size="small"
            locale={{ emptyText: '还没有素材，上传你的第一条视频/图片吧' }}
          />
        </div>
      </div>

      <Modal title="新建分类" open={folderModalOpen}
        onOk={handleCreateFolder} onCancel={() => setFolderModalOpen(false)}>
        <Input placeholder="分类名称" value={newFolderName}
          onChange={(e) => setNewFolderName(e.target.value)} />
      </Modal>
    </div>
  );
}
