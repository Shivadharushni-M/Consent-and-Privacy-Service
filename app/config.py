from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/consent_db"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    API_KEY: str = "local-dev-key"  # API key for authentication
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DEBUG: bool = False
    MAXMIND_ACCOUNT_ID: Optional[str] = None
    MAXMIND_LICENSE_KEY: Optional[str] = None
    # Event forwarding provider URLs (optional)
    ANALYTICS_WEBHOOK_URL: Optional[str] = None
    ADS_WEBHOOK_URL: Optional[str] = None
    EMAIL_WEBHOOK_URL: Optional[str] = None
    LOCATION_WEBHOOK_URL: Optional[str] = None

    # Google Analytics Configuration (optional)
    GA_MEASUREMENT_ID: Optional[str] = None
    GA_API_SECRET: Optional[str] = None

    # Google Ads Configuration (optional)
    GOOGLE_ADS_CUSTOMER_ID: Optional[str] = None
    GOOGLE_ADS_DEVELOPER_TOKEN: Optional[str] = None
    GOOGLE_ADS_CLIENT_ID: Optional[str] = None
    GOOGLE_ADS_CLIENT_SECRET: Optional[str] = None
    GOOGLE_ADS_REFRESH_TOKEN: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Ignore extra fields in .env file
    )

settings = Settings()
