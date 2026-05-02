from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str
    anthropic_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: int = 0
    getcourse_api_key: str = ""
    getcourse_account: str = ""
    diary_topic_name: str = "Дневник успеха"
    diary_topic_id: int = 0
    admin_password: str = "changeme"
    admin_secret_key: str = "change-this-secret-key-32-chars!!"

settings = Settings()
