from youtube_transcript_api.formatters import SRTFormatter, WebVTTFormatter
from src.utils.logger import logger


class TranscriptionFormatter:
    """Formateador de transcripciones a diferentes formatos"""

    def __init__(self):
        self.srt_formatter = SRTFormatter()
        self.vtt_formatter = WebVTTFormatter()

    def format_as_srt(self, segments: list) -> str:
        """
        Convierte segmentos de transcripción a formato SRT

        Args:
            segments: Lista de segmentos con timestamps

        Returns:
            String en formato SRT

        Formato SRT:
        1
        00:00:00,000 --> 00:00:05,000
        Hola a todos, bienvenidos al stream

        2
        00:00:05,000 --> 00:00:10,000
        Hoy vamos a hablar sobre Python
        """
        try:
            srt_content = self.srt_formatter.format_transcript(segments)
            logger.debug(f"Transcripción formateada a SRT: {len(srt_content)} caracteres")
            return srt_content

        except Exception as e:
            logger.error(f"Error formateando a SRT: {e}", exc_info=True)
            raise

    def format_as_vtt(self, segments: list) -> str:
        """
        Convierte segmentos de transcripción a formato WebVTT

        Args:
            segments: Lista de segmentos con timestamps

        Returns:
            String en formato WebVTT

        Formato VTT:
        WEBVTT

        00:00:00.000 --> 00:00:05.000
        Hola a todos, bienvenidos al stream

        00:00:05.000 --> 00:00:10.000
        Hoy vamos a hablar sobre Python
        """
        try:
            vtt_content = self.vtt_formatter.format_transcript(segments)
            logger.debug(f"Transcripción formateada a VTT: {len(vtt_content)} caracteres")
            return vtt_content

        except Exception as e:
            logger.error(f"Error formateando a VTT: {e}", exc_info=True)
            raise

    def format_as_text(self, segments: list) -> str:
        """
        Convierte segmentos a texto plano (sin timestamps)

        Args:
            segments: Lista de segmentos

        Returns:
            String de texto plano
        """
        try:
            text = "\n".join(segment["text"] for segment in segments)
            logger.debug(f"Transcripción formateada a texto plano: {len(text)} caracteres")
            return text

        except Exception as e:
            logger.error(f"Error formateando a texto: {e}", exc_info=True)
            raise

    def get_statistics(self, segments: list) -> dict:
        """
        Obtiene estadísticas de una transcripción

        Args:
            segments: Lista de segmentos

        Returns:
            Dict con estadísticas (duración, palabras, etc.)
        """
        if not segments:
            return {}

        try:
            # Duración total
            first_start = segments[0]["start"]
            last_end = segments[-1]["start"] + segments[-1]["duration"]
            total_duration = last_end - first_start

            # Contar palabras
            all_text = " ".join(segment["text"] for segment in segments)
            word_count = len(all_text.split())

            # Palabras por minuto
            wpm = (word_count / total_duration) * 60 if total_duration > 0 else 0

            stats = {
                "total_segments": len(segments),
                "total_duration_seconds": total_duration,
                "total_duration_minutes": total_duration / 60,
                "total_characters": len(all_text),
                "total_words": word_count,
                "words_per_minute": round(wpm, 2),
            }

            logger.debug(f"Estadísticas de transcripción: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error calculando estadísticas: {e}", exc_info=True)
            return {}
