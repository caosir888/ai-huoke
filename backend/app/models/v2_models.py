"""
V2.0 新增数据模型 — 多平台矩阵 + 获客采集 + 自动回复 + 微信引流

这些模型将在 V2.0 Week 9-12 逐步激活使用。
"""
import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ============================================================
# V2.0 模型 1: 账号分组 (W9)
# ============================================================
class AccountGroup(Base):
    """平台账号分组 — 按地区/门店/自定义分组管理"""
    __tablename__ = "account_groups"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    parent_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ============================================================
# V2.0 模型 2: 批量分发任务 (W10)
# ============================================================
class BatchPublishTask(Base):
    """批量分发 — 一键发布到多个平台账号"""
    __tablename__ = "batch_publish_tasks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), index=True)
    video_url: Mapped[str] = mapped_column(String(500))
    title_template: Mapped[str] = mapped_column(String(500))  # AI差异化标题模板
    account_ids: Mapped[list] = mapped_column(JSON, default=[])  # 目标账号ID列表
    group_ids: Mapped[list] = mapped_column(JSON, default=[])  # 目标分组ID列表
    strategy: Mapped[str] = mapped_column(String(20), default="spread")  # spread集中/interval分散/smart智能
    interval_minutes: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/processing/done/partial_fail
    results: Mapped[dict] = mapped_column(JSON, default={})  # 每个子任务的结果
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ============================================================
# V2.0 模型 3: 获客采集任务 (W11)
# ============================================================
class LeadCollectionTask(Base):
    """获客采集 — 从公域平台收集潜在客户线索"""
    __tablename__ = "lead_collection_tasks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    source_type: Mapped[str] = mapped_column(String(20))  # keyword/competitor/video_link
    source_value: Mapped[str] = mapped_column(Text)  # 关键词/竞品账号/视频链接
    platforms: Mapped[list] = mapped_column(JSON, default=[])  # ["douyin", "xhs"]
    filters: Mapped[dict] = mapped_column(JSON, default={})  # 筛选条件
    daily_limit: Mapped[int] = mapped_column(Integer, default=100)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/running/paused/done
    collected_count: Mapped[int] = mapped_column(Integer, default=0)
    last_run_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Lead(Base):
    """采集到的线索/潜在客户"""
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), index=True)
    task_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("lead_collection_tasks.id"))
    platform: Mapped[str] = mapped_column(String(20))
    platform_user_id: Mapped[str] = mapped_column(String(100))
    nickname: Mapped[str] = mapped_column(String(200))
    avatar: Mapped[str] = mapped_column(String(500), nullable=True)
    comment_content: Mapped[str] = mapped_column(Text, nullable=True)
    source_info: Mapped[dict] = mapped_column(JSON, default={})  # 来源视频/搜索关键词
    intent_score: Mapped[int] = mapped_column(Integer, default=0)  # AI意向评分 0-100
    status: Mapped[str] = mapped_column(String(20), default="new")  # new/contacted/converted/ignored
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ============================================================
# V2.0 模型 4: 自动回复规则 (W12)
# ============================================================
class AutoReplyRule(Base):
    """自动回复 — 私信和评论的自动回复规则"""
    __tablename__ = "auto_reply_rules"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), index=True)
    platform_account_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("platform_accounts.id"))
    name: Mapped[str] = mapped_column(String(200))
    trigger_type: Mapped[str] = mapped_column(String(20))  # dm私信/comment评论/both
    trigger_keywords: Mapped[list] = mapped_column(JSON, default=[])  # 触发关键词
    match_mode: Mapped[str] = mapped_column(String(20), default="fuzzy")  # exact精确/fuzzy模糊
    reply_content: Mapped[str] = mapped_column(Text)
    reply_level: Mapped[int] = mapped_column(Integer, default=1)  # 1-3级对话
    parent_rule_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=True)  # 多级回复父规则
    daily_limit: Mapped[int] = mapped_column(Integer, default=200)
    effective_hours: Mapped[dict] = mapped_column(JSON, default={})  # {"start": "08:00", "end": "22:00"}
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AutoReplyLog(Base):
    """自动回复执行日志"""
    __tablename__ = "auto_reply_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key, default=gen_uuid)
    rule_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("auto_reply_rules.id"))
    platform: Mapped[str] = mapped_column(String(20))
    target_user: Mapped[str] = mapped_column(String(200))
    trigger_content: Mapped[str] = mapped_column(Text)
    reply_content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="sent")  # sent/failed/blocked
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ============================================================
# V2.0 模型 5: 微信联系人 (W12)
# ============================================================
class WechatContact(Base):
    """从公域引流到微信的联系人"""
    __tablename__ = "wechat_contacts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), index=True)
    lead_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("leads.id"), nullable=True)
    wechat_id: Mapped[str] = mapped_column(String(100))
    nickname: Mapped[str] = mapped_column(String(200))
    avatar: Mapped[str] = mapped_column(String(500), nullable=True)
    source_channel: Mapped[str] = mapped_column(String(50))  # douyin_dm/kuaishou_comment/xhs_dm
    source_detail: Mapped[str] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=[])
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    follow_stage: Mapped[str] = mapped_column(String(30), default="new")  # new/contacted/interested/negotiating/deal/lost
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_contact_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
