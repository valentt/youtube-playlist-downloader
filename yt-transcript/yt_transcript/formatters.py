"""Output format converters for transcripts."""

from typing import List, Dict, Any
from datetime import datetime
import json


def format_timestamp(seconds: float, srt_format: bool = False) -> str:
    """
    Format seconds as timestamp.

    Args:
        seconds: Time in seconds
        srt_format: If True, format as SRT (HH:MM:SS,mmm), else as simple (HH:MM:SS or MM:SS)

    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)

    if srt_format:
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    else:
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"


class TextFormatter:
    """Format transcript as plain text."""

    @staticmethod
    def format(
        transcript_data: List[Dict[str, Any]],
        video_id: str,
        language: str,
        is_generated: bool,
        include_timestamps: bool = True,
        include_header: bool = True
    ) -> str:
        """
        Format transcript as plain text.

        Args:
            transcript_data: List of transcript entries
            video_id: YouTube video ID
            language: Language code
            is_generated: Whether transcript is auto-generated
            include_timestamps: Whether to include timestamps
            include_header: Whether to include file header

        Returns:
            Formatted text string
        """
        lines = []

        if include_header:
            lines.append(f"YouTube Transcript")
            lines.append("=" * 80)
            lines.append(f"Video ID: {video_id}")
            lines.append(f"Video URL: https://www.youtube.com/watch?v={video_id}")
            lines.append(f"Language: {language}")
            lines.append(f"Type: {'Auto-generated' if is_generated else 'Manual'}")
            lines.append(f"Downloaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("=" * 80)
            lines.append("")

        if include_timestamps:
            lines.append("TRANSCRIPT WITH TIMESTAMPS:")
            lines.append("-" * 80)
            lines.append("")

            for entry in transcript_data:
                start_time = entry.get('start', 0)
                text = entry.get('text', '').strip()
                timestamp = format_timestamp(start_time)
                lines.append(f"[{timestamp}] {text}")

            lines.append("")
            lines.append("=" * 80)
            lines.append("FULL TEXT (no timestamps):")
            lines.append("=" * 80)
            lines.append("")

        # Full text without timestamps
        full_text = " ".join(entry.get('text', '').strip() for entry in transcript_data)
        lines.append(full_text)

        return "\n".join(lines)


class SRTFormatter:
    """Format transcript as SRT (SubRip) subtitle file."""

    @staticmethod
    def format(
        transcript_data: List[Dict[str, Any]],
        video_id: str = None,
        language: str = None,
        is_generated: bool = None
    ) -> str:
        """
        Format transcript as SRT file.

        Args:
            transcript_data: List of transcript entries
            video_id: YouTube video ID (unused, for compatibility)
            language: Language code (unused, for compatibility)
            is_generated: Whether transcript is auto-generated (unused, for compatibility)

        Returns:
            SRT formatted string
        """
        lines = []

        for i, entry in enumerate(transcript_data, 1):
            start_time = entry.get('start', 0)
            duration = entry.get('duration', 0)
            end_time = start_time + duration
            text = entry.get('text', '').strip()

            # SRT format:
            # 1
            # 00:00:00,000 --> 00:00:05,000
            # Subtitle text here
            #
            lines.append(str(i))
            lines.append(f"{format_timestamp(start_time, True)} --> {format_timestamp(end_time, True)}")
            lines.append(text)
            lines.append("")

        return "\n".join(lines)


class VTTFormatter:
    """Format transcript as WebVTT subtitle file."""

    @staticmethod
    def format(
        transcript_data: List[Dict[str, Any]],
        video_id: str = None,
        language: str = None,
        is_generated: bool = None
    ) -> str:
        """
        Format transcript as WebVTT file.

        Args:
            transcript_data: List of transcript entries
            video_id: YouTube video ID (unused, for compatibility)
            language: Language code (unused, for compatibility)
            is_generated: Whether transcript is auto-generated (unused, for compatibility)

        Returns:
            WebVTT formatted string
        """
        lines = ["WEBVTT", ""]

        for entry in transcript_data:
            start_time = entry.get('start', 0)
            duration = entry.get('duration', 0)
            end_time = start_time + duration
            text = entry.get('text', '').strip()

            # WebVTT uses . instead of , for milliseconds
            start = format_timestamp(start_time, True).replace(',', '.')
            end = format_timestamp(end_time, True).replace(',', '.')

            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")

        return "\n".join(lines)


class JSONFormatter:
    """Format transcript as JSON."""

    @staticmethod
    def format(
        transcript_data: List[Dict[str, Any]],
        video_id: str,
        language: str,
        is_generated: bool
    ) -> str:
        """
        Format transcript as JSON.

        Args:
            transcript_data: List of transcript entries
            video_id: YouTube video ID
            language: Language code
            is_generated: Whether transcript is auto-generated

        Returns:
            JSON formatted string
        """
        output = {
            "video_id": video_id,
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "language": language,
            "is_generated": is_generated,
            "downloaded_at": datetime.now().isoformat(),
            "transcript": transcript_data
        }

        return json.dumps(output, indent=2, ensure_ascii=False)


def get_formatter(format_type: str):
    """
    Get formatter class for specified format type.

    Args:
        format_type: One of 'text', 'srt', 'vtt', 'json'

    Returns:
        Formatter class

    Raises:
        ValueError: If format type is unknown
    """
    formatters = {
        'text': TextFormatter,
        'srt': SRTFormatter,
        'vtt': VTTFormatter,
        'json': JSONFormatter,
    }

    formatter = formatters.get(format_type.lower())
    if not formatter:
        raise ValueError(f"Unknown format: {format_type}. Supported: {', '.join(formatters.keys())}")

    return formatter
