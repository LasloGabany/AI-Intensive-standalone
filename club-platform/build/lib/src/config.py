from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str
    telegram_bot_token: str
    telegram_chat_id: int
    getcourse_api_key: str
    getcourse_account: str
    diary_topic_name: str = "Дневник успеха"

    class Config:
        env_file = ".env"

settings = Settings()
