import pytest

from app.classifier.keyword_rule import KeywordRuleClassifier
from app.datasource.schemas import VideoMeta

KEYWORDS_CONFIG = {
    "knowledge_course": {
        "high_precision": ["知识付费", "卖课", "训练营"],
        "medium_precision": ["干货", "副业", "技能提升", "学习方法"],
    }
}


@pytest.fixture
def classifier():
    return KeywordRuleClassifier(KEYWORDS_CONFIG)


def make_video(title="", description="", author_bio=""):
    return VideoMeta(
        video_id="v001", platform="douyin",
        title=title, author_id="a001", author_name="测试账号",
        description=description, author_bio=author_bio,
    )


def test_high_precision_keyword_match(classifier):
    video = make_video(title="知识付费变现全攻略")
    result = classifier.classify(video, "knowledge_course")
    assert result is not None
    assert result.confidence >= 0.9
    assert result.stage == "rule"
    assert result.label == "knowledge_course"


def test_medium_precision_multi_match(classifier):
    video = make_video(title="副业干货分享，技能提升必看")
    result = classifier.classify(video, "knowledge_course")
    assert result is not None
    assert result.confidence >= 0.8


def test_medium_precision_single_match(classifier):
    video = make_video(title="今天分享一些干货")
    result = classifier.classify(video, "knowledge_course")
    assert result is not None
    assert result.confidence == 0.7


def test_no_match_returns_none(classifier):
    video = make_video(title="今天去海边玩了好开心")
    result = classifier.classify(video, "knowledge_course")
    assert result is None


def test_unknown_track_returns_none(classifier):
    video = make_video(title="知识付费")
    result = classifier.classify(video, "nonexistent_track")
    assert result is None


def test_match_in_description(classifier):
    video = make_video(title="今日分享", description="本视频包含知识付费内容")
    result = classifier.classify(video, "knowledge_course")
    assert result is not None
    assert result.confidence >= 0.9


def test_match_in_author_bio(classifier):
    video = make_video(title="日常分享", author_bio="专注知识付费领域")
    result = classifier.classify(video, "knowledge_course")
    assert result is not None
