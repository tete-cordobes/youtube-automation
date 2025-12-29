from googleapiclient.discovery import Resource
from src.utils.logger import logger
from src.utils.retry import retry_on_api_error
from datetime import datetime, timedelta


class StreamDetector:
    """Detector de videos de YouTube (streams y videos normales)"""

    @retry_on_api_error
    def find_new_streams(
        self, youtube: Resource, channel_id: str, max_results: int = 10, only_livestreams: bool = False
    ) -> list[str]:
        """
        Encuentra videos recientes del canal (streams finalizados y videos normales)

        Args:
            youtube: Cliente API de YouTube autenticado
            channel_id: ID del canal a monitorear
            max_results: Máximo número de resultados (default: 10)
            only_livestreams: Si es True, solo devuelve livestreams (default: False para todos los videos)

        Returns:
            Lista de video IDs encontrados

        Quota cost: 100 unidades
        """
        try:
            # Buscar videos del canal publicados en últimos 30 días
            published_after = (datetime.utcnow() - timedelta(days=30)).isoformat() + "Z"

            logger.info(f"Buscando videos en canal {channel_id}...")

            request = youtube.search().list(
                part="snippet",
                channelId=channel_id,
                type="video",
                maxResults=max_results,
                order="date",
                publishedAfter=published_after,
            )

            response = request.execute()
            items = response.get("items", [])

            if not items:
                logger.info("No se encontraron videos nuevos")
                return []

            # Extraer IDs de videos
            video_ids = [item["id"]["videoId"] for item in items]

            logger.info(f"Encontrados {len(video_ids)} videos: {video_ids}")

            # Si only_livestreams es True, filtrar solo livestreams
            if only_livestreams:
                livestream_ids = self._filter_livestreams(youtube, video_ids)
                logger.info(f"{len(livestream_ids)} son streams: {livestream_ids}")
                return livestream_ids

            # De lo contrario, devolver todos los videos
            logger.info(f"Procesando todos los {len(video_ids)} videos")
            return video_ids

        except Exception as e:
            logger.error(f"Error buscando streams: {e}", exc_info=True)
            raise

    @retry_on_api_error
    def _filter_livestreams(self, youtube: Resource, video_ids: list[str]) -> list[str]:
        """
        Filtra videos que fueron livestreams

        Args:
            youtube: Cliente API de YouTube
            video_ids: Lista de IDs a verificar

        Returns:
            Lista de IDs que fueron livestreams

        Quota cost: 1 unidad por video
        """
        if not video_ids:
            return []

        try:
            # Obtener detalles de videos (hasta 50 por request)
            request = youtube.videos().list(
                part="liveStreamingDetails,snippet", id=",".join(video_ids)
            )

            response = request.execute()
            items = response.get("items", [])

            livestream_ids = []

            for item in items:
                video_id = item["id"]
                # Verificar si tiene liveStreamingDetails
                if "liveStreamingDetails" in item:
                    # Verificar que el stream haya finalizado
                    live_details = item["liveStreamingDetails"]
                    if "actualEndTime" in live_details:
                        livestream_ids.append(video_id)
                        title = item["snippet"]["title"]
                        logger.debug(
                            f"Stream finalizado encontrado: {video_id} - {title}"
                        )

            return livestream_ids

        except Exception as e:
            logger.error(f"Error filtrando livestreams: {e}", exc_info=True)
            raise

    @retry_on_api_error
    def get_all_channel_videos(
        self, youtube: Resource, channel_id: str, max_results: int = 500
    ) -> list[str]:
        """
        Obtiene TODOS los videos del canal (sin límite de fecha).

        Args:
            youtube: Cliente API de YouTube autenticado
            channel_id: ID del canal
            max_results: Máximo número de videos a obtener

        Returns:
            Lista de todos los video IDs del canal

        Quota cost: 100 unidades por página de 50 resultados
        """
        try:
            logger.info(f"Obteniendo TODOS los videos del canal {channel_id}...")

            all_video_ids = []
            next_page_token = None

            while len(all_video_ids) < max_results:
                request = youtube.search().list(
                    part="id",
                    channelId=channel_id,
                    type="video",
                    maxResults=min(50, max_results - len(all_video_ids)),
                    order="date",
                    pageToken=next_page_token,
                )

                response = request.execute()
                items = response.get("items", [])

                if not items:
                    break

                video_ids = [item["id"]["videoId"] for item in items]
                all_video_ids.extend(video_ids)

                logger.info(f"  Obtenidos {len(all_video_ids)} videos hasta ahora...")

                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break

            logger.info(f"Total: {len(all_video_ids)} videos encontrados en el canal")
            return all_video_ids

        except Exception as e:
            logger.error(f"Error obteniendo todos los videos: {e}", exc_info=True)
            raise

    @retry_on_api_error
    def get_video_info(self, youtube: Resource, video_id: str) -> dict:
        """
        Obtiene información detallada de un video

        Args:
            youtube: Cliente API de YouTube
            video_id: ID del video

        Returns:
            Dict con información del video (título, descripción, etc.)

        Quota cost: 1 unidad
        """
        try:
            request = youtube.videos().list(part="snippet,liveStreamingDetails", id=video_id)

            response = request.execute()
            items = response.get("items", [])

            if not items:
                logger.warning(f"Video {video_id} no encontrado")
                return {}

            video = items[0]
            snippet = video.get("snippet", {})

            return {
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "published_at": snippet.get("publishedAt", ""),
                "channel_id": snippet.get("channelId", ""),
            }

        except Exception as e:
            logger.error(f"Error obteniendo info del video {video_id}: {e}", exc_info=True)
            raise
