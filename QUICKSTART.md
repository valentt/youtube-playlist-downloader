# Quick Start Guide

Get started with YouTube Playlist Downloader in 5 minutes!

## Installation

### Step 1: Install Python 3.8+

If not already installed:
- **Windows**: Download from [python.org](https://www.python.org/downloads/)
- **Linux**: Usually pre-installed, or `sudo apt install python3 python3-pip`
- **macOS**: `brew install python3`

### Step 2: Install FFmpeg

Required for video processing:

```bash
# Windows (with Chocolatey)
choco install ffmpeg

# Linux (Ubuntu/Debian)
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### Step 3: Run Setup Script

Navigate to the project directory and run the automated setup:

**Windows:**
```bash
cd "youtube playlist downloader"
setup.bat
```

**Linux/macOS:**
```bash
cd "youtube playlist downloader"
chmod +x setup.sh
./setup.sh
```

This will:
- Create an isolated virtual environment
- Install all Python dependencies
- Set everything up automatically

**That's it!** You're ready to use the application.

## Quick Usage

### GUI (Easiest)

**Windows:**
```bash
run_gui.bat
```

**Linux/macOS:**
```bash
./run_gui.sh
```

Then:
1. Paste a playlist URL
2. Click "Fetch"
3. Go to "Videos" tab
4. Click "Download Playlist"

### CLI (Fast)

**Note:** Use `run_cli.bat` on Windows or `./run_cli.sh` on Linux/macOS.

**Public playlist:**
```bash
# Fetch metadata
./run_cli.sh fetch "https://www.youtube.com/playlist?list=PLAYLIST_ID"

# Download videos
./run_cli.sh download PLAYLIST_ID
```

**Private playlist (requires authentication):**
```bash
# 1. Export cookies from your browser (use browser extension)
# 2. Set cookies file
./run_cli.sh auth set-cookies /path/to/cookies.txt

# 3. Fetch and download
./run_cli.sh fetch "https://www.youtube.com/playlist?list=PLAYLIST_ID"
./run_cli.sh download PLAYLIST_ID
```

## Common Tasks

**Note:** Examples use Linux/macOS syntax. On Windows, use `run_cli.bat` instead of `./run_cli.sh`.

### Download audio only
```bash
./run_cli.sh download PLAYLIST_ID --audio-only
```

### Download with specific quality
```bash
./run_cli.sh download PLAYLIST_ID --quality 720p
```

### Track changes without downloading
```bash
./run_cli.sh fetch "PLAYLIST_URL" --metadata-only
./run_cli.sh update "PLAYLIST_URL"
./run_cli.sh list PLAYLIST_ID --status deleted
```

### View all playlists
```bash
./run_cli.sh playlists
```

### Filter videos
```bash
# Show only deleted videos
./run_cli.sh list PLAYLIST_ID --status deleted

# Show only private videos
./run_cli.sh list PLAYLIST_ID --status private

# Show videos not yet downloaded
./run_cli.sh list PLAYLIST_ID --downloaded no
```

## Where are my files?

- **Virtual environment**: `venv/` (Python packages, auto-created by setup)
- **Downloaded videos**: `downloads/Playlist Name/001 - Video Title.mp4`
- **Metadata**: `playlists/PLAYLIST_ID/current_state.json`
- **Version history**: `playlists/PLAYLIST_ID/version_history.json`
- **Config**: `~/.ytpl_downloader/` (cookies, OAuth tokens)

**Note:** The `venv/` folder contains your isolated Python environment. Don't delete it!

## Need Help?

See the full [README.md](README.md) for detailed documentation.

## Pro Tips

1. **Use launcher scripts**: Always use `run_cli.bat`/`run_gui.bat` (Windows) or `./run_cli.sh`/`./run_gui.sh` (Linux/macOS) - they handle the virtual environment automatically
2. **Parallel downloads**: Use `--workers 10` for faster downloads (default is 5)
3. **Resume**: If interrupted, just run the download command again - it resumes automatically
4. **Metadata only**: Use `--metadata-only` to track playlists without downloading (saves disk space)
5. **Regular updates**: Run `update` command periodically to track which videos become private/deleted
6. **Export cookies**: For private playlists, export fresh cookies every few weeks as they expire
7. **Virtual environment**: The setup creates an isolated Python environment in `venv/` - this keeps your system Python clean
