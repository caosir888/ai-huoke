import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Boolean, Text, ForeignKey, JSON, BigInteger
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key, default=gen_uuid)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    industry: Mapped[str] = mapped_column(String(50), nullable=True)
    company_name: Mapped[str] = mapped_column(String(100), nullable=True)
    plan_type: Mapped[str] = mapped_column(String(20), default="free")  # free/basic/pro
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    accounts = relationship("PlatformAccount", back_populates="user")
    materials = relationship("Material", back_populates="user")
    edit_tasks = relationship("EditTask", back_populates="user")
    publish_tasks = relationship("PublishTask", back_populates="user")


class PlatformAccount(Base):
    __tablename__ = "platform_accounts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), index=True)
    platform: Mapped[str] = mapped_column(String(20))  # douyin/kuaishou/xhs/shipinhao
    account_name: Mapped[str] = mapped_column(String(100))
    avatar: Mapped[str] = mapped_column(String(500), nullable=True)
    fans_count: Mapped[int] = mapped_column(BigInteger, default=0)
    auth_token: Mapped[str] = mapped_column(Text, nullable=True)
    auth_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/active/expired
    expired_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="accounts")


class MaterialFolder(Base):
    __tablename__ = "material_folders"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    parent_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), index=True)
    folder_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("material_folders.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(10))  # video/image/audio
    file_name: Mapped[str] = mapped_column(String(255))
    file_url: Mapped[str] = mapped_column(String(500))
    thumbnail_url: Mapped[str] = mapped_column(String(500), nullable=True)
    duration: Mapped[float] = mapped_column(nullable=True)
    size: Mapped[int] = mapped_column(BigInteger, default=0)
    tags: Mapped[list] = mapped_column(ARRAY(String), default=[])
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="materials")


class CopywritingTemplate(Base):
    __tablename__ = "copywriting_templates"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    tags: Mapped[str] = mapped_column(String(300), nullable=True)  # #tag1 #tag2
    style: Mapped[str] = mapped_column(String(20))  # 口播/展示/促销/剧情
    source: Mapped[str] = mapped_column(String(20), default="ai")  # ai/manual/link_parse
    source_url: Mapped[str] = mapped_column(String(500), nullable=True)
    is_favorited: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EditTask(Base):
    __tablename__ = "edit_tasks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), index=True)
    material_ids: Mapped[list] = mapped_column(ARRAY(String))
    copywriting_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=True)
    template_id: Mapped[str] = mapped_column(String(50), nullable=True)  # 混剪模板标识
    params: Mapped[dict] = mapped_column(JSON, default={})  # count/duration/ratio/voice/subtitle_style
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/processing/done/failed
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    output_urls: Mapped[list] = mapped_column(ARRAY(String), default=[])
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    user = relationship("User", back_populates="edit_tasks")


class PublishTask(Base):
    __tablename__ = "publish_tasks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), index=True)
    video_url: Mapped[str] = mapped_column(String(500))
    platform_account_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("platform_accounts.id"))
    title: Mapped[str] = mapped_column(String(500))
    schedule_type: Mapped[str] = mapped_column(String(10))  # now/timed/recurring
    schedule_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/publishing/published/failed
    publish_result: Mapped[dict] = mapped_column(JSON, nullable=True)
    metrics: Mapped[dict] = mapped_column(JSON, default={})  # plays/likes/comments/shares
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="publish_tasks")


class UserQuota(Base):
    __tablename__ = "user_quotas"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), unique=True, index=True)
    daily_video_count: Mapped[int] = mapped_column(Integer, default=3)
    monthly_video_count: Mapped[int] = mapped_column(Integer, default=90)
    account_limit: Mapped[int] = mapped_column(Integer, default=1)
    storage_bytes_used: Mapped[int] = mapped_column(BigInteger, default=0)
    storage_bytes_limit: Mapped[int] = mapped_column(BigInteger, default=1073741824)  # 1GB
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
