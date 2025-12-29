import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from src.utils.logger import logger
from config.settings import settings


class StateTracker:
    """Gestiona el estado de videos procesados usando JSON"""

    def __init__(self, state_file: Path = None):
        """
        Args:
            state_file: Path al archivo de estado (default: data/state.json)
        """
        self.state_file = state_file or (settings.DATA_DIR / "state.json")
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """
        Carga estado desde archivo JSON

        Returns:
            Dict con estado de videos
        """
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    logger.info(f"Estado cargado: {len(state.get('processed_videos', {}))} videos")
                    return state
            except Exception as e:
                logger.error(f"Error cargando estado: {e}")
                return self._create_empty_state()
        else:
            logger.info("No existe archivo de estado, creando nuevo...")
            return self._create_empty_state()

    def _create_empty_state(self) -> dict:
        """
        Crea estructura vacía de estado

        Returns:
            Dict vacío con estructura correcta
        """
        return {"last_check": None, "processed_videos": {}}

    def _save_state(self):
        """Guarda estado actual a archivo JSON"""
        try:
            settings.ensure_directories()
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)

            logger.debug("Estado guardado correctamente")

        except Exception as e:
            logger.error(f"Error guardando estado: {e}", exc_info=True)
            raise

    def is_processed(self, video_id: str) -> bool:
        """
        Verifica si un video ya fue procesado exitosamente

        Args:
            video_id: ID del video a verificar

        Returns:
            True si el video está marcado como 'completed'
        """
        video_state = self.state["processed_videos"].get(video_id)

        if not video_state:
            return False

        return video_state.get("status") == "completed"

    def mark_processed(
        self,
        video_id: str,
        steps: dict,
        title: str = None,
        error: str = None,
    ):
        """
        Marca un video como procesado (exitoso o fallido)

        Args:
            video_id: ID del video
            steps: Dict con estado de cada paso (transcript, metadata, thumbnail, captions)
            title: Título del video (opcional)
            error: Mensaje de error si hubo fallo (opcional)
        """
        # Determinar estado: completed si todos los steps son True
        status = "completed" if all(steps.values()) else "failed"

        self.state["processed_videos"][video_id] = {
            "video_id": video_id,
            "title": title,
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "status": status,
            "steps": steps,
            "error": error,
        }

        self._save_state()

        log_msg = f"Video {video_id} marcado como {status}"
        if error:
            log_msg += f" (error: {error})"
        logger.info(log_msg)

    def get_video_state(self, video_id: str) -> Optional[dict]:
        """
        Obtiene el estado de un video específico

        Args:
            video_id: ID del video

        Returns:
            Dict con estado del video o None si no existe
        """
        return self.state["processed_videos"].get(video_id)

    def get_failed_videos(self) -> list[str]:
        """
        Obtiene lista de videos que fallaron en algún paso

        Returns:
            Lista de video IDs con status 'failed'
        """
        failed = [
            vid
            for vid, data in self.state["processed_videos"].items()
            if data.get("status") == "failed"
        ]

        logger.debug(f"Videos fallidos: {len(failed)}")
        return failed

    def retry_failed(self) -> list[str]:
        """
        Marca videos fallidos como no procesados para reintentar

        Returns:
            Lista de video IDs que serán reintentados
        """
        failed = self.get_failed_videos()

        for video_id in failed:
            del self.state["processed_videos"][video_id]

        self._save_state()

        logger.info(f"{len(failed)} videos marcados para reintento")
        return failed

    def update_last_check(self):
        """Actualiza timestamp de última revisión"""
        self.state["last_check"] = datetime.utcnow().isoformat() + "Z"
        self._save_state()
        logger.debug("Timestamp de última revisión actualizado")

    def get_statistics(self) -> dict:
        """
        Obtiene estadísticas del procesamiento

        Returns:
            Dict con estadísticas
        """
        videos = self.state["processed_videos"]

        completed = sum(1 for v in videos.values() if v.get("status") == "completed")
        failed = sum(1 for v in videos.values() if v.get("status") == "failed")

        stats = {
            "total_videos": len(videos),
            "completed": completed,
            "failed": failed,
            "success_rate": completed / len(videos) if len(videos) > 0 else 0,
            "last_check": self.state.get("last_check"),
        }

        return stats

    def clean_old_entries(self, days: int = 30):
        """
        Elimina entradas de videos procesados hace más de X días

        Args:
            days: Número de días para considerar entrada como vieja
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)
        cutoff_iso = cutoff.isoformat() + "Z"

        initial_count = len(self.state["processed_videos"])

        # Filtrar videos antiguos
        self.state["processed_videos"] = {
            vid: data
            for vid, data in self.state["processed_videos"].items()
            if data.get("processed_at", "") > cutoff_iso
        }

        removed = initial_count - len(self.state["processed_videos"])

        if removed > 0:
            self._save_state()
            logger.info(f"Eliminadas {removed} entradas antiguas (>{days} días)")
