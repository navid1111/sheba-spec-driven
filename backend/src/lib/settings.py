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
        description="OTP delivery provider: console, twilio, mocean, or email"
    )
    otp_ttl_seconds: int = Field(
        default=300,  # 5 minutes
        description="OTP code time-to-live in seconds"
    )
    
    # Email SMTP (required if otp_provider=email)
    smtp_host: str = Field(default="smtp.gmail.com", description="SMTP server host")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_username: str = Field(default="", description="SMTP username/email")
    smtp_password: str = Field(default="", description="SMTP password/app password")
    smtp_from_email: str = Field(default="", description="From email address")
    smtp_from_name: str = Field(default="ShoktiAI", description="From name")
    
    # Twilio (optional, required if otp_provider=twilio)
    twilio_account_sid: str = Field(default="", description="Twilio account SID")
    twilio_auth_token: str = Field(default="", description="Twilio auth token")
    twilio_from_number: str = Field(default="", description="Twilio sender phone number")
    
    # Mocean (optional, required if otp_provider=mocean)
    mocean_token: str = Field(default="", description="Mocean API token")
    mocean_from: str = Field(default="SHOKTIAI", description="Mocean sender name")
    
    # Application
    app_name: str = Field(default="ShoktiAI Backend", description="Application name")
    app_base_url: str = Field(
        default="https://app.sheba.xyz",
        description="Base URL for mobile app deep links"
    )
    debug: bool = Field(default=False, description="Debug mode")
    
    # Secret key (used for deep link tokens and other signing)
    secret_key: str = Field(
        default="change-me-in-prod-secret-key-for-tokens",
        description="Secret key for token signing and encryption"
    )
    
    
# Global settings instance
settings = Settings()
