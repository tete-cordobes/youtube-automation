from googleapiclient.discovery import Resource
from googleapiclient.http import MediaFileUpload
from pathlib import Path
from src.utils.logger import logger
from src.utils.retry import retry_on_api_error


class VideoManager:
    """Gestiona actualizaciones de metadata y thumbnails en YouTube"""

    def __init__(self, youtube: Resource):
        """
        Args:
            youtube: Cliente API de YouTube autenticado
        """
        self.youtube = youtube

    @retry_on_api_error
    def update_metadata(self, video_id: str, title: str, description: str) -> bool:
        """
        Actualiza título y descripción de un video

        Args:
            video_id: ID del video a actualizar
            title: Nuevo título (máx 100 caracteres)
            description: Nueva descripción

        Returns:
            True si se actualizó correctamente

        Quota cost: 50 unidades
        """
        try:
            # Validar longitud del título
            if len(title) > 100:
                logger.warning(f"Título muy largo ({len(title)} chars), truncando...")
                title = title[:97] + "..."

            logger.info(f"Actualizando metadata del video {video_id}...")
            logger.debug(f"Título: {title}")

            # Obtener info actual del video
            video = self.youtube.videos().list(part="snippet", id=video_id).execute()

            if not video.get("items"):
                logger.error(f"Video {video_id} no encontrado")
                return False

            snippet = video["items"][0]["snippet"]

            # Actualizar campos
            snippet["title"] = title
            snippet["description"] = description

            # Enviar actualización
            self.youtube.videos().update(
                part="snippet", body={"id": video_id, "snippet": snippet}
            ).execute()

            logger.info(f"Metadata actualizada correctamente para {video_id}")
            return True

        except Exception as e:
            logger.error(f"Error actualizando metadata: {e}", exc_info=True)
            raise

    @retry_on_api_error
    def update_thumbnail(self, video_id: str, thumbnail_path: Path) -> bool:
        """
        Sube miniatura personalizada para un video

        Args:
            video_id: ID del video
            thumbnail_path: Path al archivo de imagen

        Returns:
            True si se subió correctamente

        Quota cost: 50 unidades

        Requisitos de la miniatura:
        - Aspect ratio: 16:9
        - Formato: JPG, PNG, GIF, BMP
        - Tamaño máximo: 2MB
        - Resolución recomendada: 1280x720px
        """
        try:
            if not thumbnail_path.exists():
                logger.error(f"Archivo de thumbnail no existe: {thumbnail_path}")
                return False

            # Verificar tamaño (2MB max)
            file_size = thumbnail_path.stat().st_size
            if file_size > 2 * 1024 * 1024:  # 2MB
                logger.error(
                    f"Thumbnail muy grande: {file_size / (1024*1024):.2f}MB (máx 2MB)"
                )
                return False

            logger.info(f"Subiendo thumbnail para video {video_id}...")

            self.youtube.thumbnails().set(
                videoId=video_id, media_body=MediaFileUpload(str(thumbnail_path))
            ).execute()

            logger.info(f"Thumbnail actualizado correctamente para {video_id}")
            return True

        except Exception as e:
            logger.error(f"Error actualizando thumbnail: {e}", exc_info=True)
            raise

    @retry_on_api_error
    def get_current_metadata(self, video_id: str) -> dict:
        """
        Obtiene metadata actual de un video

        Args:
            video_id: ID del video

        Returns:
            Dict con título, descripción, etc.

        Quota cost: 1 unidad
        """
        try:
            video = self.youtube.videos().list(part="snippet", id=video_id).execute()

            if not video.get("items"):
                logger.warning(f"Video {video_id} no encontrado")
                return {}

            snippet = video["items"][0]["snippet"]

            return {
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "tags": snippet.get("tags", []),
                "category_id": snippet.get("categoryId", ""),
            }

        except Exception as e:
            logger.error(f"Error obteniendo metadata: {e}", exc_info=True)
            raise
