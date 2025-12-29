from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from src.utils.logger import logger
from src.utils.retry import retry_on_api_error
import time


class TranscriptionExtractor:
    """Extractor de transcripciones de videos de YouTube"""

    def get_transcript(self, video_id: str, language: str = "es", max_retries: int = 3) -> dict:
        """
        Extrae la transcripción de un video de YouTube

        Args:
            video_id: ID del video
            language: Código de idioma preferido (default: 'es')
            max_retries: Máximo número de reintentos si no disponible

        Returns:
            Dict con 'text' (transcripción completa) y 'segments' (segmentos con timestamps)

        Raises:
            Exception: Si no se puede obtener la transcripción

        Nota: YouTube puede tardar 5-10 minutos en generar la transcripción después
              de finalizar un stream. Esta función implementa espera y reintentos.
        """
        languages_to_try = [language, "es", "en"]

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Obteniendo transcripción del video {video_id} "
                    f"(intento {attempt + 1}/{max_retries})..."
                )

                # Intentar obtener transcripción en idiomas especificados
                # API cambió: get_transcript -> fetch
                # Ahora devuelve un FetchedTranscript con snippets
                api = YouTubeTranscriptApi()
                fetched = api.fetch(video_id, languages=languages_to_try)

                if not fetched or not fetched.snippets:
                    raise ValueError("Transcripción vacía")

                # Los snippets ya son objetos correctos
                snippets = fetched.snippets

                # Formatear a texto plano (el formatter acepta los snippets directamente)
                text_formatter = TextFormatter()
                full_text = text_formatter.format_transcript(snippets)

                logger.info(
                    f"Transcripción obtenida exitosamente: "
                    f"{len(full_text)} caracteres, "
                    f"{len(snippets)} segmentos"
                )

                # Devolver snippets originales (son objetos que funcionan con los formatters)
                return {"text": full_text, "segments": snippets}

            except Exception as e:
                logger.warning(f"Intento {attempt + 1} fallido: {e}")

                if attempt < max_retries - 1:
                    # Esperar antes de reintentar (YouTube puede estar generando)
                    wait_time = 60 * (attempt + 1)  # 60s, 120s, 180s
                    logger.info(
                        f"Transcripción no disponible aún. "
                        f"Esperando {wait_time}s antes de reintentar..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"No se pudo obtener transcripción después de "
                        f"{max_retries} intentos"
                    )
                    raise

    def get_transcript_languages(self, video_id: str) -> list:
        """
        Obtiene la lista de idiomas disponibles para transcripción

        Args:
            video_id: ID del video

        Returns:
            Lista de códigos de idioma disponibles
        """
        try:
            # API cambió: list_transcripts -> list
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)
            # transcript_list es ahora un TranscriptList
            languages = [t.language_code for t in transcript_list.transcripts]
            logger.debug(f"Idiomas de transcripción disponibles: {languages}")
            return languages

        except Exception as e:
            logger.warning(f"No se pudo obtener lista de idiomas: {e}")
            return []

    def validate_transcript(self, transcript_data: dict, min_length: int = 100) -> bool:
        """
        Valida que una transcripción sea útil

        Args:
            transcript_data: Dict con 'text' y 'segments'
            min_length: Longitud mínima del texto (caracteres)

        Returns:
            True si la transcripción es válida
        """
        if not transcript_data:
            logger.warning("Transcripción vacía")
            return False

        text = transcript_data.get("text", "")
        segments = transcript_data.get("segments", [])

        if len(text) < min_length:
            logger.warning(f"Transcripción muy corta: {len(text)} caracteres")
            return False

        if len(segments) == 0:
            logger.warning("No hay segmentos en la transcripción")
            return False

        logger.info(f"Transcripción válida: {len(text)} caracteres, {len(segments)} segmentos")
        return True
