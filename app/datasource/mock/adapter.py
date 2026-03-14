"""
Mock 数据源适配器。

返回结构真实的假数据，用于：
1. 在没有真实 API Key 时跑通完整数据流
2. 单元测试和集成测试

数据特征：
- 模拟知识卖课赛道的典型视频
- 播放量随时间自然增长（含随机波动）
- 支持多次调用返回不同快照值，模拟真实增量
"""
import random
from datetime import datetime, timedelta, timezone

from app.datasource.base import PlatformDataSource
from app.datasource.schemas import VideoMeta, VideoStats

# 种子视频库：模拟知识卖课赛道的真实内容
_MOCK_VIDEOS: list[dict] = [
    {"video_id": "mock_v001", "title": "副业变现3步走，月入过万不是梦", "author_id": "mock_a001", "author_name": "副业达人小王", "author_bio": "专注副业变现，已帮助10000+学员实现月入过万"},
    {"video_id": "mock_v002", "title": "零基础学Python，30天从入门到项目实战", "author_id": "mock_a002", "author_name": "编程老李", "author_bio": "10年编程经验，Python/AI方向"},
    {"video_id": "mock_v003", "title": "考研数学高效备考方法论，真题讲解", "author_id": "mock_a003", "author_name": "考研数学张老师", "author_bio": "考研数学辅导，清华硕士"},
    {"video_id": "mock_v004", "title": "职场PPT制作技巧，让你的汇报脱颖而出", "author_id": "mock_a004", "author_name": "职场效率姐", "author_bio": "500强HR，职场技能分享"},
    {"video_id": "mock_v005", "title": "英语口语30天突破，外教同款发音训练", "author_id": "mock_a005", "author_name": "英语教练Amy", "author_bio": "雅思8.5，专注口语突破"},
    {"video_id": "mock_v006", "title": "理财小白必看：基金定投避坑指南", "author_id": "mock_a006", "author_name": "理财师小陈", "author_bio": "持牌理财师，十年投资经验"},
    {"video_id": "mock_v007", "title": "思维导图记忆法，读书效率提升300%", "author_id": "mock_a007", "author_name": "学习博主阿强", "author_bio": "终身学习者，分享高效学习方法"},
    {"video_id": "mock_v008", "title": "自媒体变现全攻略，从0到月入5万", "author_id": "mock_a008", "author_name": "新媒体运营老胡", "author_bio": "做过百万粉账号，现帮人孵化账号"},
    {"video_id": "mock_v009", "title": "Excel数据分析实战，职场必备技能", "author_id": "mock_a004", "author_name": "职场效率姐", "author_bio": "500强HR，职场技能分享"},
    {"video_id": "mock_v010", "title": "公务员备考时间规划，上岸经验分享", "author_id": "mock_a009", "author_name": "上岸公务员小赵", "author_bio": "国考上岸，备考经验分享"},
    {"video_id": "mock_v011", "title": "抖音运营变现课，教你从0打造爆款账号", "author_id": "mock_a008", "author_name": "新媒体运营老胡", "author_bio": "做过百万粉账号，现帮人孵化账号"},
    {"video_id": "mock_v012", "title": "AI工具使用教程，效率提升10倍的秘密", "author_id": "mock_a002", "author_name": "编程老李", "author_bio": "10年编程经验，Python/AI方向"},
    {"video_id": "mock_v013", "title": "读书笔记怎么做？费曼学习法实践", "author_id": "mock_a007", "author_name": "学习博主阿强", "author_bio": "终身学习者，分享高效学习方法"},
    {"video_id": "mock_v014", "title": "CFA备考攻略，金融从业者必看", "author_id": "mock_a006", "author_name": "理财师小陈", "author_bio": "持牌理财师，十年投资经验"},
    {"video_id": "mock_v015", "title": "短视频剪辑入门教程，手机剪映全解析", "author_id": "mock_a008", "author_name": "新媒体运营老胡", "author_bio": "做过百万粉账号，现帮人孵化账号"},
    {"video_id": "mock_v016", "title": "雅思写作满分攻略，Task2模板拆解", "author_id": "mock_a005", "author_name": "英语教练Amy", "author_bio": "雅思8.5，专注口语突破"},
    {"video_id": "mock_v017", "title": "产品经理转行指南，0基础入行互联网", "author_id": "mock_a010", "author_name": "PM圈内人", "author_bio": "BAT产品总监，分享产品思维"},
    {"video_id": "mock_v018", "title": "股票入门知识，散户如何避免韭菜命运", "author_id": "mock_a006", "author_name": "理财师小陈", "author_bio": "持牌理财师，十年投资经验"},
    {"video_id": "mock_v019", "title": "写作变现：公众号/知乎接单全流程", "author_id": "mock_a001", "author_name": "副业达人小王", "author_bio": "专注副业变现，已帮助10000+学员实现月入过万"},
    {"video_id": "mock_v020", "title": "数据分析师求职必备，SQL面试题精讲", "author_id": "mock_a002", "author_name": "编程老李", "author_bio": "10年编程经验，Python/AI方向"},
]

# 基础播放量（模拟各视频的自然体量）
_BASE_PLAY_COUNTS: dict[str, int] = {
    v["video_id"]: random.randint(50_000, 5_000_000)
    for v in _MOCK_VIDEOS
}

# 关键词 → 视频 ID 映射（模拟搜索结果）
_KEYWORD_MAP: dict[str, list[str]] = {
    "知识付费": ["mock_v001", "mock_v008", "mock_v011", "mock_v019"],
    "副业": ["mock_v001", "mock_v008", "mock_v019", "mock_v015"],
    "干货": ["mock_v004", "mock_v007", "mock_v013", "mock_v009"],
    "编程": ["mock_v002", "mock_v012", "mock_v020"],
    "考研": ["mock_v003", "mock_v010"],
    "英语学习": ["mock_v005", "mock_v016"],
    "理财": ["mock_v006", "mock_v014", "mock_v018"],
    "学习方法": ["mock_v007", "mock_v013"],
    "职场": ["mock_v004", "mock_v009", "mock_v017"],
    "技能提升": ["mock_v002", "mock_v004", "mock_v009", "mock_v012"],
}

# 话题 → 视频 ID 映射（模拟话题页）
_TOPIC_MAP: dict[str, list[str]] = {
    "干货": ["mock_v001", "mock_v002", "mock_v004", "mock_v007", "mock_v012"],
    "副业": ["mock_v001", "mock_v008", "mock_v011", "mock_v019"],
    "知识": ["mock_v003", "mock_v005", "mock_v006", "mock_v013", "mock_v016"],
    "学习": ["mock_v007", "mock_v010", "mock_v013", "mock_v014"],
    "技能": ["mock_v009", "mock_v015", "mock_v017", "mock_v020"],
}

# 账号 → 视频 ID 映射（模拟账号主页）
_ACCOUNT_MAP: dict[str, list[str]] = {
    "mock_a001": ["mock_v001", "mock_v019"],
    "mock_a002": ["mock_v002", "mock_v012", "mock_v020"],
    "mock_a003": ["mock_v003"],
    "mock_a004": ["mock_v004", "mock_v009"],
    "mock_a005": ["mock_v005", "mock_v016"],
    "mock_a006": ["mock_v006", "mock_v014", "mock_v018"],
    "mock_a007": ["mock_v007", "mock_v013"],
    "mock_a008": ["mock_v008", "mock_v011", "mock_v015"],
    "mock_a009": ["mock_v010"],
    "mock_a010": ["mock_v017"],
}


def _build_video_meta(video_dict: dict) -> VideoMeta:
    """从字典构建 VideoMeta，模拟发布时间为近30天内随机。"""
    published_at = datetime.now(tz=timezone.utc) - timedelta(
        days=random.randint(0, 30),
        hours=random.randint(0, 23),
    )
    return VideoMeta(
        video_id=video_dict["video_id"],
        platform="douyin",
        title=video_dict["title"],
        author_id=video_dict["author_id"],
        author_name=video_dict["author_name"],
        author_bio=video_dict.get("author_bio", ""),
        published_at=published_at,
        tags=["知识", "干货"],
    )


def _build_video_stats(video_id: str) -> VideoStats:
    """
    构建视频播放数据快照。
    每次调用在基础播放量上叠加随机增量，模拟真实数据增长。
    """
    base = _BASE_PLAY_COUNTS.get(video_id, 100_000)
    # 模拟每次调用有 5%-30% 的随机增长
    play_count = base + random.randint(int(base * 0.05), int(base * 0.30))
    return VideoStats(
        video_id=video_id,
        platform="douyin",
        play_count=play_count,
        like_count=int(play_count * random.uniform(0.03, 0.08)),
        comment_count=int(play_count * random.uniform(0.005, 0.02)),
        share_count=int(play_count * random.uniform(0.01, 0.04)),
        collect_count=int(play_count * random.uniform(0.02, 0.06)),
        fetched_at=datetime.now(tz=timezone.utc),
    )


def _get_videos_by_ids(video_ids: list[str]) -> list[VideoMeta]:
    id_map = {v["video_id"]: v for v in _MOCK_VIDEOS}
    return [_build_video_meta(id_map[vid]) for vid in video_ids if vid in id_map]


class MockDataSource(PlatformDataSource):
    """
    Mock 数据源，返回结构真实的假数据。
    接口与真实适配器完全一致，上层业务无感知。
    """

    @property
    def platform(self) -> str:
        return "douyin"

    async def search_by_keyword(
        self, keyword: str, limit: int = 50
    ) -> list[VideoMeta]:
        # 模糊匹配关键词
        matched_ids: list[str] = []
        for key, ids in _KEYWORD_MAP.items():
            if keyword in key or key in keyword:
                matched_ids.extend(ids)

        # 去重
        seen = set()
        unique_ids = [vid for vid in matched_ids if not (vid in seen or seen.add(vid))]
        return _get_videos_by_ids(unique_ids[:limit])

    async def get_topic_videos(
        self, topic_tag: str, limit: int = 50
    ) -> list[VideoMeta]:
        video_ids = _TOPIC_MAP.get(topic_tag, list(_TOPIC_MAP.values())[0])
        return _get_videos_by_ids(video_ids[:limit])

    async def get_account_videos(
        self, account_id: str, limit: int = 30
    ) -> list[VideoMeta]:
        video_ids = _ACCOUNT_MAP.get(account_id, [])
        return _get_videos_by_ids(video_ids[:limit])

    async def fetch_stats(
        self, video_ids: list[str]
    ) -> list[VideoStats]:
        return [_build_video_stats(vid) for vid in video_ids]
