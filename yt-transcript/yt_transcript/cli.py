"""Command-line interface for YouTube Transcript Downloader."""

import click
from pathlib import Path
from typing import List, Optional
import sys

from .downloader import TranscriptDownloader, extract_video_id
from .formatters import get_formatter, TextFormatter


@click.command()
@click.argument('video_url_or_id')
@click.option(
    '--lang', '-l',
    multiple=True,
    help='Preferred language code(s) (e.g., en, es, fr). Can specify multiple: -l en -l es'
)
@click.option(
    '--format', '-f',
    type=click.Choice(['text', 'srt', 'vtt', 'json'], case_sensitive=False),
    default='text',
    help='Output format (default: text)'
)
@click.option(
    '--output', '-o',
    type=click.Path(),
    help='Output file path. If not specified, prints to stdout'
)
@click.option(
    '--no-timestamps',
    is_flag=True,
    help='Exclude timestamps from text output (text format only)'
)
@click.option(
    '--no-header',
    is_flag=True,
    help='Exclude header from text output (text format only)'
)
@click.option(
    '--list-languages',
    is_flag=True,
    help='List available languages for the video and exit'
)
@click.option(
    '--all-languages',
    is_flag=True,
    help='Download transcripts in all available languages'
)
@click.option(
    '--quiet', '-q',
    is_flag=True,
    help='Suppress progress messages'
)
def main(
    video_url_or_id: str,
    lang: tuple,
    format: str,
    output: Optional[str],
    no_timestamps: bool,
    no_header: bool,
    list_languages: bool,
    all_languages: bool,
    quiet: bool
):
    """
    Download YouTube video transcripts/captions.

    VIDEO_URL_OR_ID can be a YouTube video URL or just the video ID.

    Examples:

        \b
        # Download transcript for a video
        yt-transcript "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        \b
        # Specify language
        yt-transcript dQw4w9WgXcQ --lang es

        \b
        # Save as SRT subtitle file
        yt-transcript dQw4w9WgXcQ --format srt --output subtitles.srt

        \b
        # List available languages
        yt-transcript dQw4w9WgXcQ --list-languages

        \b
        # Download all languages
        yt-transcript dQw4w9WgXcQ --all-languages --output ./transcripts
    """
    try:
        # Extract video ID
        video_id = extract_video_id(video_url_or_id)
        if not video_id:
            click.echo(click.style(
                f"Error: Invalid YouTube URL or video ID: {video_url_or_id}",
                fg='red'
            ), err=True)
            sys.exit(1)

        downloader = TranscriptDownloader()

        # List languages mode
        if list_languages:
            _list_languages(downloader, video_id)
            return

        # Download all languages mode
        if all_languages:
            _download_all_languages(
                downloader,
                video_id,
                format,
                output,
                no_timestamps,
                no_header,
                quiet
            )
            return

        # Single language mode (default)
        _download_single(
            downloader,
            video_id,
            list(lang) if lang else None,
            format,
            output,
            no_timestamps,
            no_header,
            quiet
        )

    except KeyboardInterrupt:
        click.echo("\nCancelled by user", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'), err=True)
        sys.exit(1)


def _list_languages(downloader: TranscriptDownloader, video_id: str):
    """List available languages for a video."""
    try:
        languages = downloader.list_available_languages(video_id)

        if not languages:
            click.echo("No transcripts available for this video")
            return

        click.echo(f"\nAvailable languages for video {video_id}:")
        click.echo("-" * 60)

        for lang in languages:
            lang_type = "Auto-generated" if lang['generated'] else "Manual"
            translatable = " (translatable)" if lang['translatable'] else ""
            click.echo(f"  {lang['code']:5s} - {lang['name']:20s} [{lang_type}]{translatable}")

        click.echo(f"\nTotal: {len(languages)} language(s)")

    except Exception as e:
        click.echo(click.style(f"Error listing languages: {e}", fg='red'), err=True)
        sys.exit(1)


def _download_single(
    downloader: TranscriptDownloader,
    video_id: str,
    languages: Optional[List[str]],
    format_type: str,
    output_path: Optional[str],
    no_timestamps: bool,
    no_header: bool,
    quiet: bool
):
    """Download transcript in a single language."""
    try:
        if not quiet:
            lang_str = ", ".join(languages) if languages else "auto"
            click.echo(f"Downloading transcript for video {video_id} (language: {lang_str})...")

        # Download transcript
        transcript_data, language, is_generated = downloader.download_transcript(
            video_id,
            languages
        )

        if not quiet:
            lang_type = "auto-generated" if is_generated else "manual"
            click.echo(f"Retrieved {lang_type} transcript in '{language}'")

        # Format transcript
        formatter = get_formatter(format_type)

        if format_type == 'text':
            content = formatter.format(
                transcript_data,
                video_id,
                language,
                is_generated,
                include_timestamps=not no_timestamps,
                include_header=not no_header
            )
        else:
            content = formatter.format(
                transcript_data,
                video_id,
                language,
                is_generated
            )

        # Output
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(content, encoding='utf-8')
            if not quiet:
                click.echo(click.style(f"Saved to: {output_file}", fg='green'))
        else:
            click.echo(content)

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'), err=True)
        sys.exit(1)


def _download_all_languages(
    downloader: TranscriptDownloader,
    video_id: str,
    format_type: str,
    output_dir: Optional[str],
    no_timestamps: bool,
    no_header: bool,
    quiet: bool
):
    """Download transcripts in all available languages."""
    try:
        if not quiet:
            click.echo(f"Downloading transcripts in all available languages for video {video_id}...")

        # Get all languages
        all_transcripts = downloader.download_all_languages(video_id)

        if not all_transcripts:
            click.echo("No transcripts available for this video")
            return

        # Determine output directory
        if output_dir:
            base_dir = Path(output_dir)
        else:
            base_dir = Path(f"{video_id}_transcripts")

        base_dir.mkdir(parents=True, exist_ok=True)

        # Process each language
        for lang_code, (transcript_data, is_generated) in all_transcripts.items():
            if not quiet:
                lang_type = "auto-generated" if is_generated else "manual"
                click.echo(f"  Processing '{lang_code}' ({lang_type})...")

            # Format transcript
            formatter = get_formatter(format_type)

            if format_type == 'text':
                content = formatter.format(
                    transcript_data,
                    video_id,
                    lang_code,
                    is_generated,
                    include_timestamps=not no_timestamps,
                    include_header=not no_header
                )
            else:
                content = formatter.format(
                    transcript_data,
                    video_id,
                    lang_code,
                    is_generated
                )

            # Save to file
            ext_map = {'text': 'txt', 'srt': 'srt', 'vtt': 'vtt', 'json': 'json'}
            ext = ext_map.get(format_type, 'txt')
            output_file = base_dir / f"{video_id}_{lang_code}.{ext}"
            output_file.write_text(content, encoding='utf-8')

        if not quiet:
            click.echo(click.style(
                f"\nDownloaded {len(all_transcripts)} transcript(s) to: {base_dir}",
                fg='green'
            ))

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'), err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
