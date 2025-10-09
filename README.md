# YouTube Playlist Downloader

A comprehensive cross-platform YouTube playlist downloader with both CLI and GUI interfaces. Track playlist changes over time, download videos in various formats, and monitor which videos become private or deleted.

## Features

- **Dual Interface**: Both command-line (CLI) and graphical (GUI) interfaces
- **Cross-Platform**: Works on Windows, Linux, and macOS
- **Authentication Support**: Both browser cookies and OAuth authentication for private playlists
- **JSON Versioning**: Track playlist changes over time with complete version history
- **Status Tracking**: Monitor videos that become private, deleted, or unavailable
- **Flexible Downloads**:
  - Video quality selection (1080p default, 720p, best)
  - Audio-only downloads
  - Metadata-only mode (no video downloads)
- **Parallel Downloads**: 5 concurrent downloads by default (configurable)
- **Resume Capability**: Automatically resume interrupted downloads
- **Organized Storage**: Downloads organized in folders with playlist position numbers
- **Filtering**: Filter videos by status (live, private, deleted) and download status

## Installation

### Prerequisites

- Python 3.8 or higher
- FFmpeg (for audio extraction and video merging)

### Install FFmpeg

**Windows:**
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch
sudo pacman -S ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

### Quick Setup (Automated)

We provide automated setup scripts for easy installation with isolated virtual environment:

**Windows:**
```bash
# Navigate to the project directory
cd "youtube playlist downloader"

# Run the setup script
setup.bat
```

**Linux/macOS:**
```bash
# Navigate to the project directory
cd "youtube playlist downloader"

# Make script executable (first time only)
chmod +x setup.sh

# Run the setup script
./setup.sh
```

The setup script will:
1. Check Python installation
2. Create a virtual environment (isolated from system Python)
3. Install all dependencies
4. Display usage instructions

### Manual Setup (Alternative)

If you prefer manual installation:

```bash
# Navigate to the project directory
cd "youtube playlist downloader"

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Note:** Always activate the virtual environment before running the application:
- Windows: `venv\Scripts\activate`
- Linux/macOS: `source venv/bin/activate`

Or use the provided launcher scripts (see Usage section below).

## Authentication Setup

For **public playlists**, no authentication is needed. For **private playlists** or playlists from your account, you need to authenticate.

### Option 1: Browser Cookies (Recommended)

1. Install a browser extension to export cookies:
   - Chrome/Edge: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - Firefox: [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

2. Log into YouTube in your browser

3. Export cookies to a file (Netscape format)

4. Set the cookies file:
   ```bash
   # CLI (Windows)
   run_cli.bat auth set-cookies /path/to/cookies.txt

   # CLI (Linux/macOS)
   ./run_cli.sh auth set-cookies /path/to/cookies.txt

   # GUI: Settings tab → Set Cookies button
   ```

### Option 2: OAuth Authentication

1. Go to [Google Cloud Console](https://console.cloud.google.com/)

2. Create a new project or select existing one

3. Enable YouTube Data API v3

4. Create OAuth 2.0 credentials (Desktop application)

5. Download the `client_secrets.json` file

6. Set up OAuth:
   ```bash
   # CLI (Windows)
   run_cli.bat auth setup-oauth --client-secrets /path/to/client_secrets.json

   # CLI (Linux/macOS)
   ./run_cli.sh auth setup-oauth --client-secrets /path/to/client_secrets.json

   # GUI: Settings tab → Setup OAuth button
   ```

## Usage

### GUI Interface

Launch the GUI:

**Option 1: Using launcher scripts (recommended):**
```bash
# Windows:
run_gui.bat

# Linux/macOS:
./run_gui.sh
```

**Option 2: Manual activation:**
```bash
# Activate virtual environment first
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

# Then run
python run_gui.py
```

**Features:**
- **Playlists Tab**: Fetch new playlists, view stored playlists, update existing ones
- **Videos Tab**: View videos with filters, download playlists
- **Settings Tab**: Configure authentication, view logs

**Workflow:**
1. Enter playlist URL in the "Fetch Playlist" section
2. Click "Fetch" to download metadata
3. Switch to "Videos" tab to view and filter videos
4. Configure download options (quality, audio-only, workers)
5. Click "Download Playlist"

### CLI Interface

Launch the CLI:

**Option 1: Using launcher scripts (recommended):**
```bash
# Windows:
run_cli.bat --help

# Linux/macOS:
./run_cli.sh --help
```

**Option 2: Manual activation:**
```bash
# Activate virtual environment first
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

# Then run
python run_cli.py --help
```

#### Basic Commands

**Note:** Examples below use Linux/macOS syntax (`./run_cli.sh`). On Windows, use `run_cli.bat` instead.

**Fetch a playlist:**
```bash
./run_cli.sh fetch "https://www.youtube.com/playlist?list=PLxxxxxx"
```

**List stored playlists:**
```bash
./run_cli.sh playlists
```

**List videos in a playlist:**
```bash
./run_cli.sh list PLxxxxxx

# With filters
./run_cli.sh list PLxxxxxx --status deleted
./run_cli.sh list PLxxxxxx --status private
./run_cli.sh list PLxxxxxx --downloaded no
```

**Download a playlist:**
```bash
# Default: 1080p, 5 workers
./run_cli.sh download PLxxxxxx

# Custom options
./run_cli.sh download PLxxxxxx --quality 720p --workers 10
./run_cli.sh download PLxxxxxx --audio-only
./run_cli.sh download PLxxxxxx --metadata-only
```

**Update a playlist:**
```bash
./run_cli.sh update "https://www.youtube.com/playlist?list=PLxxxxxx"
```

**View version history:**
```bash
./run_cli.sh history PLxxxxxx
```

**Check authentication status:**
```bash
./run_cli.sh auth status
```

## Project Structure

```
youtube playlist downloader/
├── ytpl_downloader/          # Main package
│   ├── core/
│   │   ├── auth.py           # Authentication management
│   │   ├── models.py          # Data models
│   │   ├── playlist_fetcher.py # Playlist fetching
│   │   ├── storage.py         # JSON versioning
│   │   └── downloader.py      # Download management
│   ├── cli/
│   │   └── main.py           # CLI interface
│   └── gui/
│       └── main.py           # GUI interface
├── venv/                     # Virtual environment (auto-generated)
├── playlists/                # Stored playlist data (auto-generated)
│   └── {playlist_id}/
│       ├── current_state.json
│       └── version_history.json
├── downloads/                # Downloaded videos (auto-generated)
│   └── {playlist_name}/
│       ├── 001 - Video Title.mp4
│       ├── 002 - Another Video.mp4
│       └── ...
├── setup.bat                 # Windows setup script
├── setup.sh                  # Linux/macOS setup script
├── run_cli.py                # CLI entry point (Python)
├── run_cli.bat               # CLI launcher (Windows)
├── run_cli.sh                # CLI launcher (Linux/macOS)
├── run_gui.py                # GUI entry point (Python)
├── run_gui.bat               # GUI launcher (Windows)
├── run_gui.sh                # GUI launcher (Linux/macOS)
├── requirements.txt          # Python dependencies
├── setup.py                  # Package setup file
├── README.md                 # Full documentation
├── QUICKSTART.md             # Quick start guide
└── .gitignore                # Git ignore file
```

## Data Storage

### Current State JSON
Each playlist has a `current_state.json` file containing:
- Playlist metadata (title, description, channel, etc.)
- All videos with complete metadata
- Video status (live, deleted, private, unavailable)
- Download status and file paths
- Status change history for each video

### Version History JSON
Each playlist has a `version_history.json` file containing:
- List of all versions/snapshots
- For each version:
  - Timestamp
  - Videos added
  - Videos removed
  - Videos with status changes
  - Notes

### Video Metadata
For each video, we track:
- Basic info: video_id, title, channel, uploader
- Detailed metadata: upload_date, duration, description, thumbnail
- Statistics: view_count, like_count, comment_count
- Status tracking: current status, status history
- Download info: download status, file paths
- Timestamps: first_seen, last_checked, last_modified

## Examples

**Note:** Examples use Linux/macOS syntax. On Windows, replace `./run_cli.sh` with `run_cli.bat`.

### Example 1: Download a public playlist

```bash
# Fetch metadata
./run_cli.sh fetch "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"

# Download videos
./run_cli.sh download PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf
```

### Example 2: Track playlist changes over time

```bash
# Initial fetch
./run_cli.sh fetch "https://www.youtube.com/playlist?list=PLxxxxxx"

# Later, update to see changes
./run_cli.sh update "https://www.youtube.com/playlist?list=PLxxxxxx"

# View what changed
./run_cli.sh history PLxxxxxx

# List deleted videos
./run_cli.sh list PLxxxxxx --status deleted
```

### Example 3: Download only audio

```bash
./run_cli.sh download PLxxxxxx --audio-only
```

### Example 4: Metadata-only tracking

```bash
# Just track the playlist without downloading videos
./run_cli.sh fetch "https://www.youtube.com/playlist?list=PLxxxxxx" --metadata-only
```

## Troubleshooting

### Videos not downloading

1. Check authentication is set up for private playlists
2. Ensure FFmpeg is installed and in PATH
3. Try with `--quality best` instead of specific quality

### Cookies expired

Browser cookies expire periodically. Re-export cookies from your browser and update:
```bash
# Linux/macOS
./run_cli.sh auth set-cookies /path/to/new-cookies.txt

# Windows
run_cli.bat auth set-cookies /path/to/new-cookies.txt
```

### Rate limiting

If you hit YouTube rate limits, reduce parallel workers:
```bash
# Linux/macOS
./run_cli.sh download PLxxxxxx --workers 2

# Windows
run_cli.bat download PLxxxxxx --workers 2
```

### Virtual environment issues

If you get "command not found" or module import errors:
1. Make sure you ran the setup script (`setup.bat` or `./setup.sh`)
2. Use the launcher scripts (`run_cli.bat`/`run_gui.bat` or `./run_cli.sh`/`./run_gui.sh`)
3. Or manually activate: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Linux/macOS)

## Advanced Usage

### Programmatic Access

You can use the core modules directly in your Python code:

```python
from ytpl_downloader.core.auth import AuthManager
from ytpl_downloader.core.playlist_fetcher import PlaylistFetcher
from ytpl_downloader.core.storage import PlaylistStorage
from ytpl_downloader.core.downloader import DownloadManager

# Initialize
auth = AuthManager()
fetcher = PlaylistFetcher(auth)
storage = PlaylistStorage()
downloader = DownloadManager(auth, storage)

# Fetch playlist
playlist = fetcher.fetch_playlist("https://www.youtube.com/playlist?list=PLxxxxxx")

# Update and save
updated = storage.update_playlist(playlist)
storage.save_playlist(updated)

# Download
downloader.download_playlist(updated, quality="1080p", max_workers=5)
```

## Contributing

Feel free to open issues or submit pull requests for improvements!

## License

This project is for personal use. Please respect YouTube's Terms of Service.

## Acknowledgments

- Built with [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- GUI built with [PySide6](https://doc.qt.io/qtforpython/)
- CLI built with [Click](https://click.palletsprojects.com/)
