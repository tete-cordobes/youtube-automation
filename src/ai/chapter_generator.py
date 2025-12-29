from src.ai.gemini_client import GeminiClient
from src.utils.logger import logger
from config.settings import settings


class ChapterGenerator:
    """Generador de capítulos/timestamps para videos de YouTube"""

    def __init__(self):
        self.client = GeminiClient()

    def generate_chapters(self, transcript_segments: list[dict]) -> str:
        """
        Genera capítulos/timestamps basados en los segmentos de la transcripción

        Args:
            transcript_segments: Lista de segmentos con formato:
                [{"start": 0.0, "end": 5.0, "text": "..."}]

        Returns:
            String con timestamps en formato YouTube (ej: "0:00 Introducción\n1:23 Tema principal")

        Formato YouTube:
            - Los timestamps deben estar en orden cronológico
            - Formato: MM:SS o HH:MM:SS
            - Cada línea: "timestamp Título del capítulo"
            - El primer capítulo debe empezar en 0:00
        """
        try:
            logger.info("Generando capítulos para el video...")

            # Crear texto con timestamps para el análisis
            transcript_with_times = self._format_transcript_with_times(transcript_segments)

            # Generar capítulos usando IA
            chapters_text = self._generate_chapters_with_ai(transcript_with_times)

            # Validar y formatear capítulos
            formatted_chapters = self._validate_and_format_chapters(chapters_text)

            logger.info(f"Capítulos generados:\n{formatted_chapters}")

            return formatted_chapters

        except Exception as e:
            logger.error(f"Error generando capítulos: {e}", exc_info=True)
            # Devolver capítulo básico en caso de error
            return "0:00 Video completo"

    def _format_transcript_with_times(self, segments: list, sample_interval: int = 30) -> str:
        """
        Formatea la transcripción con marcas de tiempo cada N segundos

        Args:
            segments: Segmentos de transcripción (FetchedTranscriptSnippet objects)
            sample_interval: Intervalo en segundos para muestrear (default: 30s)

        Returns:
            Texto formateado con timestamps
        """
        formatted_lines = []
        current_time = 0

        for segment in segments:
            # Los segmentos son objetos con atributos .start, .duration, .text
            start_time = segment.start

            # Agregar marca de tiempo cada sample_interval segundos
            if start_time >= current_time:
                timestamp = self._seconds_to_timestamp(start_time)
                formatted_lines.append(f"[{timestamp}] {segment.text}")
                current_time += sample_interval

        return "\n".join(formatted_lines)

    def _generate_chapters_with_ai(self, transcript_with_times: str) -> str:
        """
        Genera capítulos usando IA basándose en la transcripción con timestamps

        Args:
            transcript_with_times: Transcripción con marcas de tiempo

        Returns:
            Texto con capítulos en formato YouTube
        """
        prompt = f"""Analiza esta transcripción de video con timestamps y genera capítulos significativos.

TRANSCRIPCIÓN:
{transcript_with_times[:8000]}

INSTRUCCIONES:
1. Identifica entre 5-10 momentos clave o cambios de tema en el video
2. Crea un título descriptivo y conciso (máx 50 caracteres) para cada capítulo
3. Usa los timestamps [HH:MM:SS] o [MM:SS] que aparecen en la transcripción
4. El primer capítulo DEBE empezar en 0:00

FORMATO DE SALIDA (muy importante):
0:00 Título del primer capítulo
1:23 Título del segundo capítulo
5:45 Título del tercer capítulo

REGLAS:
- Solo escribe los capítulos en el formato especificado
- No agregues explicaciones ni texto adicional
- Los títulos deben ser descriptivos pero concisos
- Los timestamps deben estar en orden cronológico

Genera los capítulos ahora:"""

        chapters = self.client.generate_text(prompt)
        return chapters.strip()

    def _validate_and_format_chapters(self, chapters_text: str) -> str:
        """
        Valida y formatea los capítulos generados por la IA

        Args:
            chapters_text: Texto con capítulos generados

        Returns:
            Texto formateado y validado
        """
        lines = chapters_text.strip().split("\n")
        valid_chapters = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Verificar formato: "MM:SS Título" o "HH:MM:SS Título"
            if ":" in line:
                parts = line.split(" ", 1)
                if len(parts) == 2:
                    timestamp, title = parts
                    # Validar que el timestamp tenga formato correcto
                    if self._is_valid_timestamp(timestamp):
                        valid_chapters.append(f"{timestamp} {title}")

        # Asegurar que el primer capítulo empiece en 0:00
        if not valid_chapters or not valid_chapters[0].startswith("0:00"):
            valid_chapters.insert(0, "0:00 Introducción")

        # Si no hay capítulos válidos, devolver uno básico
        if not valid_chapters:
            return "0:00 Video completo"

        return "\n".join(valid_chapters)

    def _is_valid_timestamp(self, timestamp: str) -> bool:
        """
        Verifica si un timestamp tiene formato válido (MM:SS o HH:MM:SS)

        Args:
            timestamp: String con el timestamp

        Returns:
            True si es válido
        """
        try:
            parts = timestamp.split(":")
            if len(parts) == 2:  # MM:SS
                minutes, seconds = map(int, parts)
                return 0 <= minutes and 0 <= seconds < 60
            elif len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = map(int, parts)
                return 0 <= hours and 0 <= minutes < 60 and 0 <= seconds < 60
            return False
        except (ValueError, AttributeError):
            return False

    def _seconds_to_timestamp(self, seconds: float) -> str:
        """
        Convierte segundos a formato timestamp (MM:SS o HH:MM:SS)

        Args:
            seconds: Tiempo en segundos

        Returns:
            String en formato timestamp
        """
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
