"""Transcript downloader module."""

from typing import List, Dict, Any, Optional, Tuple
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    YouTubeRequestFailed
)
import re


def extract_video_id(url_or_id: str) -> Optional[str]:
    """
    Extract video ID from YouTube URL or return ID if already in correct format.

    Args:
        url_or_id: YouTube URL or video ID

    Returns:
        Video ID or None if invalid
    """
    # If it's already an 11-character ID
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
        return url_or_id

    # Extract from various YouTube URL formats
    patterns = [
        r'(?:v=|/)([a-zA-Z0-9_-]{11}).*',
        r'(?:embed/)([a-zA-Z0-9_-]{11})',
        r'(?:watch\?v=)([a-zA-Z0-9_-]{11})',
        r'(?:youtu\.be/)([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)

    return None


def extract_playlist_id(url: str) -> Optional[str]:
    """
    Extract playlist ID from YouTube playlist URL.

    Args:
        url: YouTube playlist URL

    Returns:
        Playlist ID or None if invalid
    """
    patterns = [
        r'list=([a-zA-Z0-9_-]+)',
        r'playlist\?list=([a-zA-Z0-9_-]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


class TranscriptDownloader:
    """Download YouTube video transcripts."""

    def __init__(self):
        """Initialize the downloader."""
        self.api = YouTubeTranscriptApi()

    def list_available_languages(self, video_id: str) -> List[Dict[str, str]]:
        """
        List all available transcript languages for a video.

        Args:
            video_id: YouTube video ID

        Returns:
            List of dicts with language info: [{'code': 'en', 'name': 'English', 'generated': True}, ...]
        """
        try:
            transcript_list = self.api.list(video_id)
            languages = []

            for transcript in transcript_list:
                languages.append({
                    'code': transcript.language_code,
                    'name': transcript.language,
                    'generated': transcript.is_generated,
                    'translatable': transcript.is_translatable
                })

            return languages

        except Exception as e:
            raise Exception(f"Failed to list languages: {e}")

    def download_transcript(
        self,
        video_id: str,
        languages: Optional[List[str]] = None
    ) -> Tuple[List[Dict[str, Any]], str, bool]:
        """
        Download transcript for a video.

        Args:
            video_id: YouTube video ID
            languages: List of preferred language codes (e.g., ['en', 'es']).
                      If None, tries English first, then any available

        Returns:
            Tuple of (transcript_data, language_code, is_generated)

        Raises:
            TranscriptsDisabled: Transcripts are disabled for this video
            NoTranscriptFound: No transcript found in requested languages
            VideoUnavailable: Video is unavailable
            TooManyRequests: Rate limited
        """
        try:
            # Get available transcripts
            transcript_list = self.api.list(video_id)

            # Try to get transcript in preferred languages
            transcript = None
            selected_language = None

            if languages:
                # Try each preferred language
                for lang in languages:
                    try:
                        transcript = transcript_list.find_transcript([lang])
                        selected_language = lang
                        break
                    except NoTranscriptFound:
                        continue

            # If no preferred language found, try English
            if not transcript:
                try:
                    transcript = transcript_list.find_transcript(['en'])
                    selected_language = 'en'
                except NoTranscriptFound:
                    # Get any available transcript (first one)
                    try:
                        available = list(transcript_list)
                        if available:
                            transcript = available[0]
                            selected_language = transcript.language_code
                    except:
                        pass

            if not transcript:
                raise NoTranscriptFound(
                    video_id,
                    languages or ['en'],
                    transcript_list
                )

            # Fetch the actual transcript
            fetched_transcript = transcript.fetch()

            if not fetched_transcript or not fetched_transcript.snippets:
                raise NoTranscriptFound(video_id, languages or ['en'], None)

            # Convert to dict format for compatibility
            transcript_data = [
                {
                    'text': snippet.text,
                    'start': snippet.start,
                    'duration': snippet.duration
                }
                for snippet in fetched_transcript.snippets
            ]

            return transcript_data, selected_language, transcript.is_generated

        except TranscriptsDisabled:
            raise TranscriptsDisabled(video_id)
        except NoTranscriptFound:
            raise NoTranscriptFound(video_id, languages or ['en'], None)
        except VideoUnavailable:
            raise VideoUnavailable(video_id)
        except YouTubeRequestFailed as e:
            raise Exception(f"YouTube request failed: {e}")
        except Exception as e:
            raise Exception(f"Error downloading transcript: {e}")

    def download_all_languages(
        self,
        video_id: str
    ) -> Dict[str, Tuple[List[Dict[str, Any]], bool]]:
        """
        Download transcripts in all available languages.

        Args:
            video_id: YouTube video ID

        Returns:
            Dict mapping language_code to (transcript_data, is_generated)
        """
        try:
            transcript_list = self.api.list(video_id)
            results = {}

            for transcript in transcript_list:
                lang_code = transcript.language_code
                fetched_transcript = transcript.fetch()

                # Convert to dict format for compatibility
                transcript_data = [
                    {
                        'text': snippet.text,
                        'start': snippet.start,
                        'duration': snippet.duration
                    }
                    for snippet in fetched_transcript.snippets
                ]

                results[lang_code] = (transcript_data, transcript.is_generated)

            return results

        except Exception as e:
            raise Exception(f"Error downloading all languages: {e}")
