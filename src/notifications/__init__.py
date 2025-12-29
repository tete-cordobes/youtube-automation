"""Módulo de notificaciones para YouTube Podcast Processor."""

from .telegram import (
    send_telegram_notification,
    notify_video_processed,
    notify_error,
    notify_system_start,
)

__all__ = [
    "send_telegram_notification",
    "notify_video_processed",
    "notify_error",
    "notify_system_start",
]
