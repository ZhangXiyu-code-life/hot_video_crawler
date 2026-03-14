import pytest

from app.classifier.account_tag_rule import AccountTagClassifier
from app.classifier.engine import TrackClassifier
from app.classifier.keyword_rule import KeywordRuleClassifier
from app.classifier.llm_classifier import LLMClassifier
from app.classifier.schemas import TrackResult
from app.datasource.schemas import VideoMeta

KEYWORDS_CONFIG = {
    "knowledge_course": {
        "high_precision": ["知识付费", "卖课"],
        "medium_precision": ["干货", "副业"],
    }
}

TRACKS_CONFIG = {
    "tracks": [
        {
            "name": "knowledge_course",
            "llm_prompt": "判断是否是知识卖课赛道：{title} {description} {author_bio}",
        }
    ]
}


def make_video(title="", author_id="", description="", author_bio=""):
    return VideoMeta(
        video_id="v001", platform="douyin",
        title=title, author_id=author_id, author_name="测试",
        description=description, author_bio=author_bio,
    )


@pytest.fixture
def classifier_no_llm(monkeypatch):
    """不触发 LLM 的分类器（高精度关键词覆盖所有情况）。"""
    kw = KeywordRuleClassifier(KEYWORDS_CONFIG)
    acc = AccountTagClassifier({"whitelist_a001": "knowledge_course"})
    llm = LLMClassifier()
    return TrackClassifier(kw, acc, llm, TRACKS_CONFIG)


@pytest.mark.asyncio
async def test_stage1_keyword_hit(classifier_no_llm):
    video = make_video(title="知识付费全攻略")
    result = await classifier_no_llm.classify(video, "knowledge_course")
    assert result.stage == "rule"
    assert result.label == "knowledge_course"
    assert result.is_match


@pytest.mark.asyncio
async def test_stage2_account_tag_hit(classifier_no_llm):
    video = make_video(title="今天去散步了", author_id="whitelist_a001")
    result = await classifier_no_llm.classify(video, "knowledge_course")
    assert result.stage == "tag"
    assert result.confidence == 1.0
    assert result.is_match


@pytest.mark.asyncio
async def test_track_result_is_match_false_for_other(classifier_no_llm):
    result = TrackResult(label="other", confidence=0.0, stage="llm")
    assert not result.is_match


@pytest.mark.asyncio
async def test_track_result_is_match_low_confidence(classifier_no_llm):
    result = TrackResult(label="knowledge_course", confidence=0.5, stage="rule")
    assert not result.is_match


def test_account_tag_classifier_wrong_track():
    acc = AccountTagClassifier({"a001": "entertainment"})
    video = make_video(author_id="a001")
    result = acc.classify(video, "knowledge_course")
    assert result is None


def test_account_tag_classifier_unknown_account():
    acc = AccountTagClassifier({"a001": "knowledge_course"})
    video = make_video(author_id="unknown_account")
    result = acc.classify(video, "knowledge_course")
    assert result is None
