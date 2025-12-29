from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    """Configuración centralizada del sistema usando Pydantic"""

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"
    TRANSCRIPTS_DIR: Path = DATA_DIR / "transcripts"
    THUMBNAILS_DIR: Path = DATA_DIR / "thumbnails"

    # YouTube API
    YOUTUBE_CLIENT_SECRET: Path = BASE_DIR / "config" / "client_secret.json"
    YOUTUBE_OAUTH_TOKEN: Path = DATA_DIR / "youtube_token.json"
    YOUTUBE_CHANNEL_ID: str

    # Gemini API
    GEMINI_API_KEY: str
    GEMINI_TEXT_MODEL: str = "models/gemini-2.5-flash"
    GEMINI_IMAGE_MODEL: str = "gemini-3-pro-image-preview"  # Gemini 3 Pro Image

    # Processing settings
    CHECK_INTERVAL_MINUTES: int = 30
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: int = 60
    ONLY_LIVESTREAMS: bool = False  # False = procesar todos los videos, True = solo livestreams

    # Subtitle settings
    SUBTITLE_LANGUAGE: str = "es"
    SUBTITLE_FORMAT: str = "srt"

    # Chapter settings
    GENERATE_CHAPTERS: bool = True  # Generar capítulos/timestamps en la descripción

    # API Settings
    API_KEY: str = "change-me-in-production"  # API Key para autenticación
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Telegram Notifications (opcional)
    TELEGRAM_BOT_TOKEN: str = ""  # Token del bot de @BotFather
    TELEGRAM_CHAT_ID: str = ""  # Chat ID para recibir notificaciones
    TELEGRAM_ENABLED: bool = True  # Activar/desactivar notificaciones

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )

    def ensure_directories(self):
        """Crea los directorios necesarios si no existen"""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        self.THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)


# Instancia global de configuración
settings = Settings()
