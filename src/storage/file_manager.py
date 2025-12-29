from pathlib import Path
from src.utils.logger import logger
from config.settings import settings


class FileManager:
    """Gestiona el guardado y carga de archivos (transcripciones, thumbnails)"""

    def __init__(self):
        """Inicializa el gestor y asegura que existan los directorios"""
        settings.ensure_directories()

    def save_transcript_text(self, video_id: str, text: str) -> Path:
        """
        Guarda transcripción como texto plano

        Args:
            video_id: ID del video
            text: Texto de la transcripción

        Returns:
            Path al archivo guardado
        """
        try:
            file_path = settings.TRANSCRIPTS_DIR / f"{video_id}.txt"

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)

            logger.info(f"Transcripción guardada en {file_path} ({len(text)} caracteres)")
            return file_path

        except Exception as e:
            logger.error(f"Error guardando transcripción: {e}", exc_info=True)
            raise

    def save_transcript_srt(self, video_id: str, srt_content: str) -> Path:
        """
        Guarda transcripción en formato SRT

        Args:
            video_id: ID del video
            srt_content: Contenido en formato SRT

        Returns:
            Path al archivo guardado
        """
        try:
            file_path = settings.TRANSCRIPTS_DIR / f"{video_id}.srt"

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(srt_content)

            logger.info(f"Subtítulos SRT guardados en {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Error guardando SRT: {e}", exc_info=True)
            raise

    def save_transcript_vtt(self, video_id: str, vtt_content: str) -> Path:
        """
        Guarda transcripción en formato WebVTT

        Args:
            video_id: ID del video
            vtt_content: Contenido en formato VTT

        Returns:
            Path al archivo guardado
        """
        try:
            file_path = settings.TRANSCRIPTS_DIR / f"{video_id}.vtt"

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(vtt_content)

            logger.info(f"Subtítulos VTT guardados en {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Error guardando VTT: {e}", exc_info=True)
            raise

    def load_transcript(self, video_id: str) -> str:
        """
        Carga transcripción guardada (texto plano)

        Args:
            video_id: ID del video

        Returns:
            Contenido de la transcripción

        Raises:
            FileNotFoundError: Si no existe el archivo
        """
        try:
            file_path = settings.TRANSCRIPTS_DIR / f"{video_id}.txt"

            if not file_path.exists():
                raise FileNotFoundError(f"Transcripción no encontrada: {file_path}")

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            logger.debug(f"Transcripción cargada: {len(content)} caracteres")
            return content

        except Exception as e:
            logger.error(f"Error cargando transcripción: {e}", exc_info=True)
            raise

    def transcript_exists(self, video_id: str) -> bool:
        """
        Verifica si existe transcripción guardada

        Args:
            video_id: ID del video

        Returns:
            True si existe el archivo
        """
        file_path = settings.TRANSCRIPTS_DIR / f"{video_id}.txt"
        return file_path.exists()

    def thumbnail_exists(self, video_id: str) -> bool:
        """
        Verifica si existe thumbnail guardado

        Args:
            video_id: ID del video

        Returns:
            True si existe el archivo
        """
        file_path = settings.THUMBNAILS_DIR / f"{video_id}.jpg"
        return file_path.exists()

    def get_thumbnail_path(self, video_id: str) -> Path:
        """
        Obtiene path al thumbnail de un video

        Args:
            video_id: ID del video

        Returns:
            Path al archivo de thumbnail
        """
        return settings.THUMBNAILS_DIR / f"{video_id}.jpg"

    def get_srt_path(self, video_id: str) -> Path:
        """
        Obtiene path al archivo SRT de un video

        Args:
            video_id: ID del video

        Returns:
            Path al archivo SRT
        """
        return settings.TRANSCRIPTS_DIR / f"{video_id}.srt"

    def clean_files(self, video_id: str):
        """
        Elimina todos los archivos asociados a un video

        Args:
            video_id: ID del video
        """
        files_to_remove = [
            settings.TRANSCRIPTS_DIR / f"{video_id}.txt",
            settings.TRANSCRIPTS_DIR / f"{video_id}.srt",
            settings.TRANSCRIPTS_DIR / f"{video_id}.vtt",
            settings.THUMBNAILS_DIR / f"{video_id}.jpg",
        ]

        removed_count = 0
        for file_path in files_to_remove:
            if file_path.exists():
                try:
                    file_path.unlink()
                    removed_count += 1
                    logger.debug(f"Eliminado: {file_path}")
                except Exception as e:
                    logger.warning(f"No se pudo eliminar {file_path}: {e}")

        if removed_count > 0:
            logger.info(f"Eliminados {removed_count} archivos para video {video_id}")

    def list_processed_videos(self) -> list[str]:
        """
        Lista todos los video IDs que tienen archivos guardados

        Returns:
            Lista de video IDs
        """
        video_ids = set()

        # Buscar en transcripciones
        for file_path in settings.TRANSCRIPTS_DIR.glob("*.txt"):
            video_ids.add(file_path.stem)

        # Buscar en thumbnails
        for file_path in settings.THUMBNAILS_DIR.glob("*.jpg"):
            video_ids.add(file_path.stem)

        return sorted(list(video_ids))

    def get_storage_stats(self) -> dict:
        """
        Obtiene estadísticas de almacenamiento

        Returns:
            Dict con estadísticas
        """
        transcript_files = list(settings.TRANSCRIPTS_DIR.glob("*"))
        thumbnail_files = list(settings.THUMBNAILS_DIR.glob("*.jpg"))

        # Calcular tamaño total
        transcript_size = sum(f.stat().st_size for f in transcript_files if f.is_file())
        thumbnail_size = sum(f.stat().st_size for f in thumbnail_files if f.is_file())

        stats = {
            "transcript_count": len(transcript_files),
            "thumbnail_count": len(thumbnail_files),
            "transcript_size_mb": transcript_size / (1024 * 1024),
            "thumbnail_size_mb": thumbnail_size / (1024 * 1024),
            "total_size_mb": (transcript_size + thumbnail_size) / (1024 * 1024),
        }

        return stats
