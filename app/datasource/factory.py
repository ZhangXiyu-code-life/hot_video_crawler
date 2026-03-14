"""
DataSourceFactory：根据配置返回对应的数据源实例。

切换数据源只需修改 .env 中的 DATA_SOURCE 字段：
  DATA_SOURCE=mock      → MockDataSource
  DATA_SOURCE=feigua    → FeiguaDataSource
  DATA_SOURCE=chanmama  → ChanmamaDataSource
"""
from app.config import get_settings
from app.datasource.base import PlatformDataSource

settings = get_settings()


def create_datasource(redis_client=None) -> PlatformDataSource:
    source = settings.data_source

    if source == "mock":
        from app.datasource.mock.adapter import MockDataSource
        return MockDataSource()

    if source == "feigua":
        if not settings.feigua_api_key:
            raise ValueError("DATA_SOURCE=feigua 但 FEIGUA_API_KEY 未配置")
        from app.datasource.feigua.adapter import FeiguaDataSource
        return FeiguaDataSource(redis_client)

    if source == "chanmama":
        if not settings.chanmama_api_key:
            raise ValueError("DATA_SOURCE=chanmama 但 CHANMAMA_API_KEY 未配置")
        from app.datasource.chanmama.adapter import ChanmamaDataSource
        return ChanmamaDataSource()

    raise ValueError(f"不支持的数据源: {source}，可选值: mock | feigua | chanmama")
