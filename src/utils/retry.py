from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from googleapiclient.errors import HttpError
from config.settings import settings
from src.utils.logger import logger
import logging


def should_retry_http_error(exception):
    """
    Determina si un error HTTP debería reintentar

    Reintenta en:
    - Errores HTTP 5xx (servidor)
    - Errores HTTP 429 (rate limit)
    - ConnectionError

    NO reintenta en:
    - Errores HTTP 4xx (excepto 429)
    """
    if isinstance(exception, HttpError):
        # Reintentar en errores temporales del servidor
        if exception.resp.status >= 500:
            return True
        # Reintentar en rate limit
        if exception.resp.status == 429:
            return True
        return False

    if isinstance(exception, ConnectionError):
        return True

    return False


def retry_on_api_error(func):
    """
    Decorador para reintentar operaciones de API con backoff exponencial

    Configuración:
    - Máximo intentos: settings.MAX_RETRIES (default 3)
    - Backoff exponencial: 4s, 16s, 64s
    - Log antes de cada reintento
    """
    return retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((HttpError, ConnectionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )(func)


class RateLimiter:
    """Rate limiter simple basado en ventana deslizante"""

    def __init__(self, max_calls: int, period: int = 60):
        """
        Args:
            max_calls: Máximo número de llamadas permitidas
            period: Período en segundos (default: 60)
        """
        import time
        from collections import deque
        from functools import wraps

        self.max_calls = max_calls
        self.period = period
        self.calls = deque()
        self._time = time
        self._wraps = wraps

    def __call__(self, func):
        @self._wraps(func)
        def wrapper(*args, **kwargs):
            now = self._time.time()

            # Limpiar llamadas antiguas (fuera de ventana)
            while self.calls and self.calls[0] < now - self.period:
                self.calls.popleft()

            # Si alcanzamos límite, esperar
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0])
                if sleep_time > 0:
                    logger.warning(f"Rate limit alcanzado. Esperando {sleep_time:.1f}s...")
                    self._time.sleep(sleep_time)
                    # Limpiar después de dormir
                    self.calls.clear()

            # Registrar llamada
            self.calls.append(self._time.time())

            # Ejecutar función
            return func(*args, **kwargs)

        return wrapper


# Instancias de rate limiters
gemini_text_limiter = RateLimiter(max_calls=10, period=60)  # 10 RPM
gemini_image_limiter = RateLimiter(max_calls=5, period=60)  # 5 RPM (conservador)
