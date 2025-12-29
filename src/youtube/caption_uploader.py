from googleapiclient.discovery import Resource
from googleapiclient.http import MediaFileUpload
from pathlib import Path
from src.utils.logger import logger
from src.utils.retry import retry_on_api_error


class CaptionUploader:
    """Gestiona la subida de subtítulos a YouTube"""

    def __init__(self, youtube: Resource):
        """
        Args:
            youtube: Cliente API de YouTube autenticado
        """
        self.youtube = youtube

    @retry_on_api_error
    def upload_captions(
        self, video_id: str, caption_file: Path, language: str = "es", name: str = None
    ) -> bool:
        """
        Sube archivo de subtítulos a un video

        Args:
            video_id: ID del video
            caption_file: Path al archivo SRT/VTT
            language: Código de idioma (ej: 'es', 'en')
            name: Nombre descriptivo para los subtítulos

        Returns:
            True si se subió correctamente

        Quota cost: 400 unidades (operación más costosa!)
        """
        try:
            if not caption_file.exists():
                logger.error(f"Archivo de subtítulos no existe: {caption_file}")
                return False

            # Nombre por defecto
            if name is None:
                name = f"{language.upper()} (Generado automáticamente)"

            logger.info(f"Subiendo subtítulos para video {video_id} ({language})...")

            # Preparar cuerpo de la petición
            body = {
                "snippet": {
                    "videoId": video_id,
                    "language": language,
                    "name": name,
                    "isDraft": False,  # Publicar inmediatamente
                }
            }

            # Subir archivo
            media = MediaFileUpload(str(caption_file), mimetype="application/octet-stream")

            self.youtube.captions().insert(part="snippet", body=body, media_body=media).execute()

            logger.info(f"Subtítulos subidos correctamente para {video_id}")
            return True

        except Exception as e:
            logger.error(f"Error subiendo subtítulos: {e}", exc_info=True)
            raise

    @retry_on_api_error
    def list_captions(self, video_id: str) -> list:
        """
        Lista los subtítulos existentes de un video

        Args:
            video_id: ID del video

        Returns:
            Lista de subtítulos con su información

        Quota cost: 50 unidades
        """
        try:
            request = self.youtube.captions().list(part="snippet", videoId=video_id)

            response = request.execute()
            items = response.get("items", [])

            captions = []
            for item in items:
                snippet = item.get("snippet", {})
                captions.append(
                    {
                        "id": item.get("id"),
                        "language": snippet.get("language"),
                        "name": snippet.get("name"),
                        "track_kind": snippet.get("trackKind"),
                        "is_draft": snippet.get("isDraft", False),
                    }
                )

            logger.debug(f"Video {video_id} tiene {len(captions)} pistas de subtítulos")
            return captions

        except Exception as e:
            logger.error(f"Error listando subtítulos: {e}", exc_info=True)
            return []

    @retry_on_api_error
    def delete_caption(self, caption_id: str) -> bool:
        """
        Elimina un subtítulo existente

        Args:
            caption_id: ID del subtítulo a eliminar

        Returns:
            True si se eliminó correctamente

        Quota cost: 50 unidades
        """
        try:
            logger.info(f"Eliminando subtítulo {caption_id}...")

            self.youtube.captions().delete(id=caption_id).execute()

            logger.info(f"Subtítulo {caption_id} eliminado correctamente")
            return True

        except Exception as e:
            logger.error(f"Error eliminando subtítulo: {e}", exc_info=True)
            raise

    def caption_exists(self, video_id: str, language: str) -> bool:
        """
        Verifica si ya existe un subtítulo en un idioma específico

        Args:
            video_id: ID del video
            language: Código de idioma a verificar

        Returns:
            True si ya existe subtítulo en ese idioma
        """
        captions = self.list_captions(video_id)
        return any(caption["language"] == language for caption in captions)
