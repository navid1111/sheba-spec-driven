"""
Application settings loaded from environment variables.
Uses pydantic-settings for validation and .env file support.
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database
    database_url: str = Field(
        default="postgresql+psycopg2://user:pass@localhost:5432/shoktiai",
        description="PostgreSQL connection string"
    )
    
    # OpenAI
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key for AI message generation"
    )
    
    # JWT
    jwt_secret: str = Field(
        default="change-me-in-prod",
        description="Secret key for JWT token signing"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )
    jwt_expiration_minutes: int = Field(
        default=10080,  # 7 days
        description="JWT token expiration in minutes"
    )
    
    # OTP
    otp_provider: str = Field(
        default="console",
        description="OTP delivery provider: console or twilio"
    )
    otp_ttl_seconds: int = Field(
        default=300,  # 5 minutes
        description="OTP code time-to-live in seconds"
    )
    
    # Twilio (optional, required if otp_provider=twilio)
    twilio_account_sid: str = Field(default="", description="Twilio account SID")
    twilio_auth_token: str = Field(default="", description="Twilio auth token")
    twilio_from_number: str = Field(default="", description="Twilio sender phone number")
    
    # Application
    app_name: str = Field(default="ShoktiAI Backend", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    
    
# Global settings instance
settings = Settings()
