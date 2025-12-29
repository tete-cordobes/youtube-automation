"""
Módulo de notificaciones de Telegram para YouTube Podcast Processor.

Envía notificaciones a un bot de Telegram cuando:
- Se procesa un nuevo episodio
- Ocurre un error
- Se inicia el sistema
"""

import requests
from typing import Optional
import os
from pathlib import Path


def _load_telegram_config() -> tuple[Optional[str], Optional[str]]:
    """Carga la configuración de Telegram desde .env o variables de entorno."""
    # Intentar cargar desde .env
    env_path = Path(__file__).parent.parent.parent / ".env"
    env_vars = {}

    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value

    bot_token = env_vars.get('TELEGRAM_BOT_TOKEN') or os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = env_vars.get('TELEGRAM_CHAT_ID') or os.environ.get('TELEGRAM_CHAT_ID')

    return bot_token, chat_id


def send_telegram_notification(message: str, parse_mode: str = "HTML") -> bool:
    """
    Envía una notificación a Telegram.

    Args:
        message: Texto del mensaje (soporta HTML)
        parse_mode: Modo de parseo (HTML o Markdown)

    Returns:
        True si se envió correctamente, False en caso contrario
    """
    bot_token, chat_id = _load_telegram_config()

    if not bot_token or not chat_id:
        # Silenciosamente ignorar si no está configurado
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception:
        return False


def notify_video_processed(video_id: str, title: str, success: bool = True) -> bool:
    """
    Notifica cuando un video ha sido procesado.

    Args:
        video_id: ID del video de YouTube
        title: Título del video
        success: Si el procesamiento fue exitoso

    Returns:
        True si se envió la notificación
    """
    if success:
        message = (
            f"<b>Episodio procesado</b>\n\n"
            f"{title}\n\n"
            f"https://youtube.com/watch?v={video_id}"
        )
    else:
        message = (
            f"<b>Error procesando episodio</b>\n\n"
            f"{title}\n\n"
            f"https://youtube.com/watch?v={video_id}"
        )

    return send_telegram_notification(message)


def notify_error(error: str, context: Optional[str] = None) -> bool:
    """
    Notifica errores críticos.

    Args:
        error: Descripción del error
        context: Contexto adicional (ej: video_id, función)

    Returns:
        True si se envió la notificación
    """
    message = f"<b>Error:</b>\n{error}"

    if context:
        message += f"\n\n<i>Contexto: {context}</i>"

    return send_telegram_notification(message)


def notify_system_start() -> bool:
    """
    Notifica que el sistema ha iniciado.

    Returns:
        True si se envió la notificación
    """
    from datetime import datetime

    message = (
        f"<b>YouTube Processor iniciado</b>\n\n"
        f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Buscando nuevos episodios..."
    )

    return send_telegram_notification(message)


# Función de prueba
if __name__ == "__main__":
    print("Probando notificaciones de Telegram...")

    bot_token, chat_id = _load_telegram_config()

    if not bot_token or not chat_id:
        print("TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados en .env")
        print("\nAgrega estas variables a tu archivo .env:")
        print("  TELEGRAM_BOT_TOKEN=tu-token-del-bot")
        print("  TELEGRAM_CHAT_ID=tu-chat-id")
    else:
        result = send_telegram_notification(
            "<b>Test</b>\n\nNotificaciones de YouTube Processor configuradas correctamente."
        )
        if result:
            print("Notificación enviada correctamente!")
        else:
            print("Error al enviar notificación. Verifica el token y chat_id.")
