"""
V2.0 获客采集引擎 — 从公域平台采集潜在客户线索（W11激活）

采集策略：
1. 关键词采集: 搜索关键词 → 获取热门视频 → 采集评论/互动用户
2. 对标账号采集: 输入竞品账号 → 采集其粉丝/评论区活跃用户
3. 视频链接采集: 输入爆款视频链接 → 采集互动用户

意向评分(AI):
- 分析用户评论内容，判断购买意向
- 关键词加权: "多少钱"=+20, "怎么买"=+25, "在哪里"=+15, "私信"=+30
- NLP情感分析: 正面+好奇=高意向, 负面+吐槽=低意向
"""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CollectionConfig:
    source_type: str  # keyword / competitor / video_link
    source_value: str
    platforms: list[str] = field(default_factory=lambda: ["douyin"])
    max_results: int = 500
    filter_active_7d: bool = True  # 仅7天内活跃用户
    exclude_collected: bool = True  # 排除已采集
    exclude_competitors: bool = True  # 排除同行账号
    run_schedule: str = "once"  # once / daily / continuous


class IntentScorer:
    """AI意向评分引擎"""

    # 购买意向关键词权重
    INTENT_KEYWORDS = {
        "多少钱": 20, "价格": 15, "怎么买": 25, "在哪买": 20,
        "私信": 30, "加微信": 40, "联系方式": 35, "想了解": 15,
        "有兴趣": 15, "报名": 25, "预约": 25, "优惠": 10,
    }

    # 否定关键词（降低意向分）
    NEGATIVE_KEYWORDS = {
        "太贵了": -15, "算了": -10, "骗人的": -30, "不好": -10,
        "垃圾": -30, "差评": -25,
    }

    @classmethod
    def score(cls, comment_text: str) -> int:
        """根据评论文本计算意向分 (0-100)"""
        score = 0
        text_lower = comment_text.lower()

        for kw, weight in cls.INTENT_KEYWORDS.items():
            if kw in text_lower:
                score += weight

        for kw, weight in cls.NEGATIVE_KEYWORDS.items():
            if kw in text_lower:
                score += weight

        return max(0, min(100, score + 20))  # 基础分20, 上下限0-100

    @classmethod
    def classify_intent(cls, score: int) -> str:
        if score >= 70:
            return "high"  # 高意向 — 直接推送微信号
        elif score >= 40:
            return "medium"  # 中意向 — 自动回复产品信息
        return "low"  # 低意向 — 观察


class LeadCollector:
    """获客采集主引擎"""

    def __init__(self):
        pass

    async def run_collection_task(self, task_id: str, config: CollectionConfig):
        """
        执行一个采集任务:
        1. 根据source_type选择采集策略
        2. 按平台并发采集
        3. AI评分去重
        4. 写入数据库
        """
        pass

    async def collect_from_keyword(self, keyword: str, platform: str, limit: int) -> list:
        """关键词搜索采集"""
        pass

    async def collect_from_competitor(self, competitor_id: str, platform: str, limit: int) -> list:
        """对标账号采集"""
        pass

    async def collect_from_video(self, video_url: str, platform: str, limit: int) -> list:
        """视频链接采集"""
        pass
