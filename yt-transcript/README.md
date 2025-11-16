# yt-transcript - YouTube Transcript Downloader

A lightweight, standalone CLI tool for downloading YouTube video transcripts (captions/subtitles) in multiple formats.

## Features

- Download transcripts from YouTube videos
- Support for both auto-generated and manual captions
- Multiple language support with automatic fallback
- Export in multiple formats: Text, SRT, VTT, JSON
- Download all available languages at once
- No authentication required for public videos
- Fast and lightweight (no video download needed)

## Installation

### From Source

```bash
cd yt-transcript
pip install -e .
```

### Requirements

- Python 3.8+
- `youtube-transcript-api>=0.6.0`
- `click>=8.1.7`

## Usage

### Basic Examples

```bash
# Download transcript for a video
yt-transcript "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Using just the video ID
yt-transcript dQw4w9WgXcQ

# Specify language
yt-transcript dQw4w9WgXcQ --lang es

# Try multiple languages (fallback)
yt-transcript dQw4w9WgXcQ --lang es --lang en

# Save to file
yt-transcript dQw4w9WgXcQ --output transcript.txt
```

### Output Formats

```bash
# Export as SRT subtitle file
yt-transcript dQw4w9WgXcQ --format srt --output subtitles.srt

# Export as WebVTT
yt-transcript dQw4w9WgXcQ --format vtt --output subtitles.vtt

# Export as JSON (with metadata)
yt-transcript dQw4w9WgXcQ --format json --output transcript.json

# Plain text without timestamps
yt-transcript dQw4w9WgXcQ --no-timestamps
```

### Language Options

```bash
# List available languages for a video
yt-transcript dQw4w9WgXcQ --list-languages

# Download all available languages
yt-transcript dQw4w9WgXcQ --all-languages

# Download all languages to specific directory
yt-transcript dQw4w9WgXcQ --all-languages --output ./transcripts
```

### Advanced Options

```bash
# Quiet mode (no progress messages)
yt-transcript dQw4w9WgXcQ --quiet --output transcript.txt

# Text format without header
yt-transcript dQw4w9WgXcQ --no-header --output transcript.txt

# Combine options
yt-transcript dQw4w9WgXcQ --lang en --format srt --output en_subtitles.srt --quiet
```

## Output Format Examples

### Text Format (default)

```
YouTube Transcript
================================================================================
Video ID: dQw4w9WgXcQ
Video URL: https://www.youtube.com/watch?v=dQw4w9WgXcQ
Language: en
Type: Auto-generated
Downloaded: 2025-11-16 14:30:00
================================================================================

TRANSCRIPT WITH TIMESTAMPS:
--------------------------------------------------------------------------------

[00:00] Welcome to this tutorial
[00:05] Today we're going to learn about Python
[00:10] Let's get started with the basics
...

================================================================================
FULL TEXT (no timestamps):
================================================================================

Welcome to this tutorial Today we're going to learn about Python...
```

### SRT Format

```srt
1
00:00:00,000 --> 00:00:05,000
Welcome to this tutorial

2
00:00:05,000 --> 00:00:10,000
Today we're going to learn about Python

3
00:00:10,000 --> 00:00:15,000
Let's get started with the basics
```

### VTT Format

```
WEBVTT

00:00:00.000 --> 00:00:05.000
Welcome to this tutorial

00:00:05.000 --> 00:00:10.000
Today we're going to learn about Python
```

### JSON Format

```json
{
  "video_id": "dQw4w9WgXcQ",
  "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "language": "en",
  "is_generated": true,
  "downloaded_at": "2025-11-16T14:30:00",
  "transcript": [
    {
      "text": "Welcome to this tutorial",
      "start": 0.0,
      "duration": 5.0
    },
    ...
  ]
}
```

## Command-Line Options

```
Options:
  -l, --lang TEXT          Preferred language code(s). Can specify multiple.
  -f, --format [text|srt|vtt|json]
                          Output format (default: text)
  -o, --output PATH       Output file path (default: stdout)
  --no-timestamps         Exclude timestamps (text format only)
  --no-header            Exclude header (text format only)
  --list-languages       List available languages and exit
  --all-languages        Download transcripts in all languages
  -q, --quiet            Suppress progress messages
  --help                 Show this message and exit
```

## Use Cases

### 1. Content Analysis
```bash
# Extract transcript for text analysis
yt-transcript VIDEO_ID --format json --output data.json
```

### 2. Create Subtitles
```bash
# Download SRT file for video editing
yt-transcript VIDEO_ID --format srt --output subtitles.srt
```

### 3. Multi-language Content
```bash
# Download English and Spanish versions
yt-transcript VIDEO_ID --lang en --output en.txt
yt-transcript VIDEO_ID --lang es --output es.txt

# Or download all at once
yt-transcript VIDEO_ID --all-languages --output ./translations
```

### 4. Research & Archival
```bash
# Save transcripts in all formats
yt-transcript VIDEO_ID --format text --output transcript.txt
yt-transcript VIDEO_ID --format srt --output subtitles.srt
yt-transcript VIDEO_ID --format json --output metadata.json
```

## Language Codes

Common language codes:
- `en` - English
- `es` - Spanish
- `fr` - French
- `de` - German
- `it` - Italian
- `pt` - Portuguese
- `ru` - Russian
- `ja` - Japanese
- `ko` - Korean
- `zh` - Chinese

Use `--list-languages` to see all available languages for a specific video.

## Error Handling

The tool handles various error conditions gracefully:

- **No transcript available**: Clear error message
- **Language not found**: Automatic fallback to English or first available
- **Video unavailable**: Appropriate error message
- **Rate limiting**: Informative error with retry suggestion

## Technical Details

- **No video download**: Uses YouTube Transcript API (no video processing)
- **No FFmpeg required**: Pure Python implementation
- **Fast execution**: API-based, typically <2 seconds per transcript
- **Cross-platform**: Works on Windows, Linux, macOS
- **No authentication**: Works with public videos (no API key needed)

## Limitations

- Only works with videos that have transcripts/captions enabled
- Cannot retrieve transcripts from private/deleted videos
- Subject to YouTube's rate limiting (usually not an issue)
- Auto-generated transcripts may have errors

## Troubleshooting

### "No transcript found"
- Video doesn't have captions/transcripts enabled
- Try `--list-languages` to see what's available

### "Rate limited"
- YouTube is temporarily blocking requests
- Wait a few minutes and try again

### "Video unavailable"
- Video is private, deleted, or region-blocked
- Cannot download transcripts from unavailable videos

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
python -m pytest tests/

# Check code style
flake8 yt_transcript/
```

## License

MIT License - see LICENSE file

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Credits

Built with:
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) - Transcript retrieval
- [Click](https://click.palletsprojects.com/) - CLI framework

## Related Projects

- [YouTube Playlist Downloader](https://github.com/valentt/youtube-playlist-downloader) - Full-featured playlist downloader with video/audio/comments

## Support

For issues and feature requests, please use the [GitHub Issues](https://github.com/valentt/yt-transcript/issues) page.

---

**Made with ❤️ by the YouTube Tools community**
