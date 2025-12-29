import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from config.settings import settings


def setup_logger(name: str = "youtube_automation", level: int = logging.INFO) -> logging.Logger:
    """
    Configura logger con rotación de archivos y output a consola

    Args:
        name: Nombre del logger
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Evitar duplicación de handlers
    if logger.handlers:
        return logger

    # Formatter con timestamp
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler con rotación (10MB max, 5 backups)
    settings.ensure_directories()
    log_file = settings.LOGS_DIR / "app.log"

    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 10MB
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler (solo INFO y superior)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)

    # Agregar handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Instancia global del logger
logger = setup_logger()
