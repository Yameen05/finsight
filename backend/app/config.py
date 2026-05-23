from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(default="", description="OpenAI API key")

    pinecone_api_key: str = Field(default="", description="Pinecone API key")
    pinecone_index_name: str = Field(default="finsight-filings")
    pinecone_cloud: str = Field(default="aws")
    pinecone_region: str = Field(default="us-east-1")

    sec_user_agent: str = Field(
        default="FinSight Research contact@example.com",
        description="SEC EDGAR requires a descriptive User-Agent with contact info.",
    )

    news_api_key: str = Field(default="", description="NewsAPI.org key for the news agent")
    news_lookback_days: int = Field(default=30, ge=1, le=30)
    news_max_articles: int = Field(default=30, ge=1, le=100)

    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dim: int = Field(default=1536)
    llm_model: str = Field(default="gpt-4o-mini")

    cors_origins: str = Field(default="http://localhost:5173")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
