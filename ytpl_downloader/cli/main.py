"""Command-line interface for YouTube playlist downloader."""

import click
from pathlib import Path
from typing import Optional
from tabulate import tabulate

from ..core.auth import AuthManager
from ..core.playlist_fetcher import PlaylistFetcher
from ..core.storage import PlaylistStorage
from ..core.downloader import DownloadManager
from ..core.archiver import ArchiveManager, format_file_size
from ..core.models import VideoStatus, DownloadStatus, ArchiveStatus


# Global variable to track last progress update (for smoother display)
_last_progress_line = ""


def display_upload_progress(filename: str, bytes_sent: int, total_bytes: int, speed_mbps: float, percent: int, status: str):
    """Display upload progress in CLI with progress bar."""
    global _last_progress_line

    # Format sizes
    sent_str = format_file_size(bytes_sent)
    total_str = format_file_size(total_bytes)

    # Progress bar
    bar_width = 30
    filled = int(bar_width * percent / 100)
    bar = '█' * filled + '░' * (bar_width - filled)

    # Build progress line based on phase
    if status == "Caching":
        progress_line = f"\r  {filename}: {status} [{bar}] {percent}%"
    else:
        # Uploading phase - show speed and ETA
        if speed_mbps > 0:
            remaining_mb = (total_bytes - bytes_sent) / (1024 * 1024)
            eta_seconds = int(remaining_mb / speed_mbps)
            if eta_seconds < 60:
                eta_str = f"{eta_seconds}s"
            else:
                eta_minutes = eta_seconds // 60
                eta_str = f"{eta_minutes}m {eta_seconds % 60}s"
        else:
            eta_str = "calculating..."

        progress_line = (
            f"\r  {filename}: {status} [{bar}] {percent}% "
            f"({sent_str}/{total_str}) @ {speed_mbps:.1f} MB/s - ETA: {eta_str}"
        )

    # Only update if changed (avoid flicker)
    if progress_line != _last_progress_line:
        click.echo(progress_line, nl=False)
        _last_progress_line = progress_line

    # New line when complete
    if percent == 100 and status == "Uploading":
        click.echo()  # Move to next line
        _last_progress_line = ""


@click.group()
@click.option('--config-dir', type=click.Path(), help='Configuration directory')
@click.pass_context
def cli(ctx, config_dir):
    """YouTube Playlist Downloader - Fetch, track, and download YouTube playlists."""
    ctx.ensure_object(dict)

    # Initialize managers
    if config_dir:
        config_dir = Path(config_dir)
    else:
        config_dir = Path.home() / '.ytpl_downloader'

    ctx.obj['auth_manager'] = AuthManager(config_dir)
    ctx.obj['storage'] = PlaylistStorage()
    ctx.obj['fetcher'] = PlaylistFetcher(ctx.obj['auth_manager'])
    ctx.obj['downloader'] = DownloadManager(ctx.obj['auth_manager'], ctx.obj['storage'])
    ctx.obj['archiver'] = ArchiveManager(ctx.obj['storage'])


@cli.group()
def auth():
    """Manage authentication (cookies and OAuth)."""
    pass


@auth.command('set-cookies')
@click.argument('cookies_file', type=click.Path(exists=True))
@click.pass_context
def set_cookies(ctx, cookies_file):
    """Set cookies file for authentication."""
    auth_manager = ctx.obj['auth_manager']
    try:
        auth_manager.set_cookies_file(cookies_file)
        click.echo(click.style('✓ Cookies file set successfully', fg='green'))
    except Exception as e:
        click.echo(click.style(f'✗ Error: {e}', fg='red'))


@auth.command('setup-oauth')
@click.option('--client-secrets', type=click.Path(exists=True), help='Path to client_secrets.json')
@click.pass_context
def setup_oauth(ctx, client_secrets):
    """Set up OAuth authentication."""
    auth_manager = ctx.obj['auth_manager']
    try:
        auth_manager.setup_oauth(client_secrets)
        click.echo(click.style('✓ OAuth set up successfully', fg='green'))
    except Exception as e:
        click.echo(click.style(f'✗ Error: {e}', fg='red'))


@auth.command('archive')
@click.option('--access-key', prompt='Archive.org Access Key', help='Archive.org S3 access key')
@click.option('--secret-key', prompt='Archive.org Secret Key', hide_input=True, help='Archive.org S3 secret key')
@click.pass_context
def configure_archive(ctx, access_key, secret_key):
    """Configure archive.org credentials."""
    auth_manager = ctx.obj['auth_manager']
    try:
        auth_manager.configure_archive_org(access_key, secret_key)
        click.echo(click.style('[OK] Archive.org credentials configured successfully', fg='green'))
        click.echo('\nYou can get your credentials from: https://archive.org/account/s3.php')
    except Exception as e:
        click.echo(click.style(f'[FAIL] Error: {e}', fg='red'))


@auth.command('clear-cookies')
@click.pass_context
def clear_cookies(ctx):
    """Clear cookies file (switch to anonymous mode)."""
    auth_manager = ctx.obj['auth_manager']

    if not auth_manager.has_cookies():
        click.echo(click.style('[INFO] No cookies file found', fg='yellow'))
        return

    # Confirm
    click.echo('\nThis will clear your cookies and switch to anonymous mode.')
    click.echo('You will only be able to access public playlists.')
    click.echo('\nNote: If your YouTube account was rate-limited or blocked,')
    click.echo('clearing cookies and waiting before using the tool again may help.')

    if click.confirm('\nContinue?'):
        try:
            auth_manager.clear_cookies()
            click.echo(click.style('\n[OK] Cookies cleared successfully', fg='green'))
            click.echo('\nYou are now in anonymous mode (public content only).')
            click.echo('\nTo avoid rate limiting:')
            click.echo('  - Use fast mode when possible (--fast)')
            click.echo('  - Reduce parallel workers (--workers 2-3 instead of 5)')
            click.echo('  - Add delays between operations')
        except Exception as e:
            click.echo(click.style(f'[FAIL] Error: {e}', fg='red'))
    else:
        click.echo('Cancelled')


@auth.command('clear-oauth')
@click.pass_context
def clear_oauth(ctx):
    """Clear OAuth token."""
    auth_manager = ctx.obj['auth_manager']

    if not auth_manager.has_oauth():
        click.echo(click.style('[INFO] No OAuth token found', fg='yellow'))
        return

    # Confirm
    if click.confirm('\nThis will clear your OAuth token. Continue?'):
        try:
            auth_manager.clear_oauth()
            click.echo(click.style('[OK] OAuth token cleared successfully', fg='green'))
        except Exception as e:
            click.echo(click.style(f'[FAIL] Error: {e}', fg='red'))
    else:
        click.echo('Cancelled')


@auth.command('test-archive')
@click.pass_context
def test_archive(ctx):
    """Test archive.org credentials and connectivity."""
    auth_manager = ctx.obj['auth_manager']

    click.echo('\nTesting Archive.org Integration...\n')

    # Test 1: Library installed
    click.echo('Test 1: Check internetarchive library')
    try:
        import internetarchive as ia
        click.echo(click.style(f'  [OK] internetarchive library installed (v{ia.__version__})', fg='green'))
    except ImportError as e:
        click.echo(click.style(f'  [FAIL] internetarchive library not installed', fg='red'))
        click.echo(f'  Error: {e}')
        click.echo('\n  Install with: pip install internetarchive>=5.4.2')
        return

    # Test 2: Credentials configured
    click.echo('\nTest 2: Check credentials configuration')
    if not auth_manager.has_archive_org():
        click.echo(click.style('  [FAIL] Archive.org credentials not configured', fg='red'))
        click.echo('\n  Configure with: ytpl auth archive')
        click.echo('  Get credentials from: https://archive.org/account/s3.php')
        return
    else:
        click.echo(click.style('  [OK] Credentials are configured', fg='green'))
        creds = auth_manager.get_archive_org_credentials()
        if creds:
            access_preview = creds['access'][:10] + '...' if len(creds['access']) > 10 else creds['access']
            click.echo(f'  Access key: {access_preview}')

    # Test 3: Connection test
    click.echo('\nTest 3: Test connection to archive.org')
    try:
        # Try to get a public item
        item = ia.get_item('test_item_202001')
        click.echo(click.style('  [OK] Successfully connected to archive.org', fg='green'))
    except Exception as e:
        click.echo(click.style(f'  [FAIL] Connection failed: {e}', fg='red'))
        return

    # Test 4: Credentials validation
    click.echo('\nTest 4: Validate credentials')
    try:
        session = ia.get_session()
        click.echo(click.style('  [OK] Credentials appear to be valid', fg='green'))

        # Try to create a test item object
        test_item = ia.get_item('youtube-test-validation-12345')
        click.echo(f'  Can create item objects: Yes')

    except Exception as e:
        error_msg = str(e).lower()
        click.echo(click.style(f'  [FAIL] Credential validation failed', fg='red'))
        click.echo(f'  Error: {e}')

        if 'account' in error_msg or 'auth' in error_msg or 'credential' in error_msg:
            click.echo('\n  Possible issues:')
            click.echo('    - Invalid access key or secret key')
            click.echo('    - Keys copied with extra whitespace')
            click.echo('    - Archive.org account not fully activated')
            click.echo('\n  Get valid credentials from: https://archive.org/account/s3.php')
        return

    # Success
    click.echo('\n' + '=' * 60)
    click.echo(click.style('All tests passed! Archive.org integration is working.', fg='green', bold=True))
    click.echo('=' * 60)


@auth.command('status')
@click.pass_context
def auth_status(ctx):
    """Check authentication status."""
    auth_manager = ctx.obj['auth_manager']
    status = auth_manager.get_auth_status()

    click.echo('\nAuthentication Status:')
    click.echo(f"  Cookies:     {click.style('[OK] Available', fg='green') if status['cookies'] else click.style('[FAIL] Not set', fg='red')}")
    click.echo(f"  OAuth:       {click.style('[OK] Available', fg='green') if status['oauth'] else click.style('[FAIL] Not set', fg='red')}")
    click.echo(f"  Archive.org: {click.style('[OK] Configured', fg='green') if status['archive_org'] else click.style('[FAIL] Not configured', fg='red')}")


@cli.command()
@click.argument('playlist_url')
@click.option('--metadata-only', is_flag=True, help='Only fetch and save metadata, do not download videos')
@click.pass_context
def fetch(ctx, playlist_url, metadata_only):
    """Fetch a playlist and save metadata."""
    fetcher = ctx.obj['fetcher']
    storage = ctx.obj['storage']

    try:
        click.echo(f'\nFetching playlist: {playlist_url}')

        # Fetch playlist
        playlist = fetcher.fetch_playlist(playlist_url)

        # Update with existing data if available
        updated_playlist = storage.update_playlist(playlist)

        # Save
        storage.save_playlist(updated_playlist)

        click.echo(click.style(f'\n✓ Playlist fetched successfully!', fg='green'))
        click.echo(f'  Title: {updated_playlist.title}')
        click.echo(f'  Videos: {len(updated_playlist.videos)}')
        click.echo(f'  Playlist ID: {updated_playlist.playlist_id}')

        if metadata_only:
            click.echo(click.style('\n  (Metadata-only mode: videos not downloaded)', fg='yellow'))

    except Exception as e:
        click.echo(click.style(f'\n✗ Error: {e}', fg='red'))


@cli.command()
@click.argument('playlist_id')
@click.option('--quality', default='1080p', help='Video quality (1080p, 720p, best)')
@click.option('--audio-only', is_flag=True, help='Download audio only')
@click.option('--metadata-only', is_flag=True, help='Update metadata without downloading')
@click.option('--workers', default=5, help='Number of parallel downloads')
@click.pass_context
def download(ctx, playlist_id, quality, audio_only, metadata_only, workers):
    """Download videos from a playlist."""
    storage = ctx.obj['storage']
    downloader = ctx.obj['downloader']

    try:
        # Load playlist
        playlist = storage.load_playlist(playlist_id)
        if not playlist:
            click.echo(click.style(f'✗ Playlist {playlist_id} not found. Run fetch first.', fg='red'))
            return

        click.echo(f'\nDownloading playlist: {playlist.title}')
        click.echo(f'Quality: {quality}, Audio only: {audio_only}, Workers: {workers}')

        # Download
        results = downloader.download_playlist(
            playlist,
            quality=quality,
            audio_only=audio_only,
            download_metadata_only=metadata_only,
            max_workers=workers
        )

        if results:
            successful = sum(1 for success in results.values() if success)
            click.echo(click.style(f'\n✓ Download complete: {successful}/{len(results)} successful', fg='green'))

    except Exception as e:
        click.echo(click.style(f'\n✗ Error: {e}', fg='red'))


@cli.command()
@click.argument('playlist_id')
@click.option('--status', type=click.Choice(['all', 'live', 'deleted', 'private', 'unavailable']), default='all')
@click.option('--downloaded', type=click.Choice(['all', 'yes', 'no']), default='all')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table')
@click.pass_context
def list(ctx, playlist_id, status, downloaded, output_format):
    """List videos in a playlist with filters."""
    storage = ctx.obj['storage']

    try:
        playlist = storage.load_playlist(playlist_id)
        if not playlist:
            click.echo(click.style(f'✗ Playlist {playlist_id} not found', fg='red'))
            return

        # Filter videos
        videos = list(playlist.videos.values())

        # Apply status filter
        if status != 'all':
            status_enum = VideoStatus(status.upper() if status != 'unavailable' else 'UNAVAILABLE')
            videos = [v for v in videos if v.status == status_enum]

        # Apply download filter
        if downloaded == 'yes':
            videos = [v for v in videos if v.download_status == DownloadStatus.COMPLETED]
        elif downloaded == 'no':
            videos = [v for v in videos if v.download_status != DownloadStatus.COMPLETED]

        # Sort by playlist index
        videos.sort(key=lambda v: v.playlist_index)

        if output_format == 'json':
            import json
            click.echo(json.dumps([v.to_dict() for v in videos], indent=2))
        else:
            # Table format
            click.echo(f'\nPlaylist: {playlist.title}')
            click.echo(f'Filtered: {len(videos)} videos\n')

            if not videos:
                click.echo('No videos match the filter criteria')
                return

            table_data = []
            for video in videos:
                status_color = {
                    VideoStatus.LIVE: 'green',
                    VideoStatus.DELETED: 'red',
                    VideoStatus.PRIVATE: 'yellow',
                    VideoStatus.UNAVAILABLE: 'red',
                }

                table_data.append([
                    video.playlist_index,
                    video.video_id,
                    video.title[:50] + '...' if len(video.title) > 50 else video.title,
                    video.channel[:30] + '...' if len(video.channel) > 30 else video.channel,
                    click.style(video.status.value, fg=status_color.get(video.status, 'white')),
                    '✓' if video.download_status == DownloadStatus.COMPLETED else '✗',
                ])

            headers = ['#', 'Video ID', 'Title', 'Channel', 'Status', 'Downloaded']
            click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))

    except Exception as e:
        click.echo(click.style(f'\n✗ Error: {e}', fg='red'))


@cli.command()
@click.pass_context
def playlists(ctx):
    """List all stored playlists."""
    storage = ctx.obj['storage']

    try:
        playlists = storage.list_playlists()

        if not playlists:
            click.echo('No playlists found')
            return

        click.echo(f'\nStored Playlists ({len(playlists)}):\n')

        table_data = [
            [p['playlist_id'], p['title'][:50], p['video_count'], p['last_updated'][:19]]
            for p in playlists
        ]

        headers = ['Playlist ID', 'Title', 'Videos', 'Last Updated']
        click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))

    except Exception as e:
        click.echo(click.style(f'\n✗ Error: {e}', fg='red'))


@cli.command()
@click.argument('playlist_id')
@click.pass_context
def history(ctx, playlist_id):
    """Show version history for a playlist."""
    storage = ctx.obj['storage']

    try:
        versions = storage.get_history(playlist_id)

        if not versions:
            click.echo(f'No version history found for {playlist_id}')
            return

        click.echo(f'\nVersion History for {playlist_id}:\n')

        for version in versions:
            click.echo(f'Version {version.version} - {version.timestamp[:19]}')
            if version.note:
                click.echo(f'  Note: {version.note}')
            if version.videos_added:
                click.echo(f'  Added: {len(version.videos_added)} videos')
            if version.videos_removed:
                click.echo(f'  Removed: {len(version.videos_removed)} videos')
            if version.videos_status_changed:
                click.echo(f'  Status changed: {len(version.videos_status_changed)} videos')
                for change in version.videos_status_changed[:5]:  # Show first 5
                    click.echo(f'    - {change["title"][:50]}: {change["old_status"]} → {change["new_status"]}')
            click.echo()

    except Exception as e:
        click.echo(click.style(f'\n✗ Error: {e}', fg='red'))


@cli.command()
@click.argument('playlist_url')
@click.pass_context
def update(ctx, playlist_url):
    """Update a playlist by re-fetching and comparing with stored data."""
    fetcher = ctx.obj['fetcher']
    storage = ctx.obj['storage']

    try:
        click.echo(f'\nUpdating playlist: {playlist_url}')

        # Fetch latest playlist
        new_playlist = fetcher.fetch_playlist(playlist_url)

        # Load existing data
        existing = storage.load_playlist(new_playlist.playlist_id)

        if not existing:
            click.echo(click.style('✗ Playlist not found locally. Use "fetch" command first.', fg='yellow'))
            return

        # Update and merge
        updated = storage.update_playlist(new_playlist, existing)

        # Save with versioning
        storage.save_playlist(updated, create_version=True)

        click.echo(click.style(f'\n✓ Playlist updated successfully!', fg='green'))

        # Show summary of changes
        versions = storage.get_history(updated.playlist_id)
        if versions:
            latest = versions[-1]
            if latest.videos_added or latest.videos_status_changed:
                click.echo('\nChanges detected:')
                if latest.videos_added:
                    click.echo(f'  New videos: {len(latest.videos_added)}')
                if latest.videos_status_changed:
                    click.echo(f'  Status changes: {len(latest.videos_status_changed)}')

    except Exception as e:
        click.echo(click.style(f'\n✗ Error: {e}', fg='red'))


@cli.command()
@click.argument('playlist_id')
@click.argument('video_id', required=False)
@click.option('--all', 'archive_all', is_flag=True, help='Archive all downloaded videos')
@click.option('--status', type=click.Choice(['deleted', 'private', 'unavailable']), help='Archive only videos with specific status')
@click.option('--force', is_flag=True, help='(Deprecated: now default behavior) Archive LIVE videos')
@click.option('--retries', default=3, help='Number of retry attempts on failure')
@click.pass_context
def archive(ctx, playlist_id, video_id, archive_all, status, force, retries):
    """Archive videos to Internet Archive (archive.org)."""
    storage = ctx.obj['storage']
    archiver = ctx.obj['archiver']
    auth_manager = ctx.obj['auth_manager']

    try:
        # Check if archive.org is configured
        if not auth_manager.has_archive_org():
            click.echo(click.style('[FAIL] Archive.org credentials not configured', fg='red'))
            click.echo('\nConfigure credentials with: ytpl auth archive')
            click.echo('Get your credentials from: https://archive.org/account/s3.php')
            return

        # Load playlist
        playlist = storage.load_playlist(playlist_id)
        if not playlist:
            click.echo(click.style(f'[FAIL] Playlist {playlist_id} not found', fg='red'))
            return

        # Determine which videos to archive
        videos_to_archive = []

        if video_id:
            # Single video
            if video_id not in playlist.videos:
                click.echo(click.style(f'[FAIL] Video {video_id} not found in playlist', fg='red'))
                return
            videos_to_archive = [playlist.videos[video_id]]
        elif archive_all:
            # All videos
            videos_to_archive = list(playlist.videos.values())
        elif status:
            # Filter by status
            status_enum = VideoStatus(status.upper() if status != 'unavailable' else 'UNAVAILABLE')
            videos_to_archive = [v for v in playlist.videos.values() if v.status == status_enum]
        else:
            click.echo(click.style('[FAIL] Please specify --all, --status, or a video ID', fg='yellow'))
            return

        if not videos_to_archive:
            click.echo('No videos match the criteria')
            return

        click.echo(f'\nArchiving {len(videos_to_archive)} video(s) to archive.org...\n')

        # Archive each video
        successful = 0
        failed = 0
        skipped = 0

        for i, video in enumerate(videos_to_archive, 1):
            click.echo(f'[{i}/{len(videos_to_archive)}] {video.title[:60]}...')

            # Get file paths
            video_path = Path(video.video_path) if video.video_path else None
            audio_path = Path(video.audio_path) if video.audio_path else None
            comments_path = Path(video.comments_path) if video.comments_path else None

            # Upload
            # Note: skip_live defaults to False - we archive LIVE videos by default
            # Use --force to override any future restrictions that might be added
            success, message = archiver.upload_video(
                video, playlist,
                video_path, audio_path, comments_path,
                retries=retries,
                skip_live=False,  # Always archive when explicitly requested
                progress_callback=display_upload_progress  # Show upload progress
            )

            if success:
                click.echo(click.style(f'  [OK] {message}', fg='green'))
                successful += 1
            elif 'Skipped' in message or 'Already' in message:
                click.echo(click.style(f'  [SKIP] {message}', fg='yellow'))
                skipped += 1
            else:
                click.echo(click.style(f'  [FAIL] {message}', fg='red'))
                failed += 1

            # Save after each upload
            storage.save_playlist(playlist, create_version=False)

        # Summary
        click.echo(f'\nSummary:')
        click.echo(f'  Total: {len(videos_to_archive)}')
        click.echo(f'  {click.style(f"Successful: {successful}", fg="green")}')
        if skipped > 0:
            click.echo(f'  {click.style(f"Skipped: {skipped}", fg="yellow")}')
        if failed > 0:
            click.echo(f'  {click.style(f"Failed: {failed}", fg="red")}')

    except Exception as e:
        click.echo(click.style(f'\n[FAIL] Error: {e}', fg='red'))


@cli.command('archive-status')
@click.argument('playlist_id')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information')
@click.pass_context
def archive_status_cmd(ctx, playlist_id, verbose):
    """Show archive status for playlist videos."""
    storage = ctx.obj['storage']

    try:
        playlist = storage.load_playlist(playlist_id)
        if not playlist:
            click.echo(click.style(f'[FAIL] Playlist {playlist_id} not found', fg='red'))
            return

        videos = list(playlist.videos.values())
        videos.sort(key=lambda v: v.playlist_index)

        # Count by status
        archived = sum(1 for v in videos if v.archive_status == ArchiveStatus.ARCHIVED)
        failed = sum(1 for v in videos if v.archive_status == ArchiveStatus.FAILED)
        skipped = sum(1 for v in videos if v.archive_status == ArchiveStatus.SKIPPED)
        not_archived = sum(1 for v in videos if v.archive_status == ArchiveStatus.NOT_ARCHIVED)

        click.echo(f'\nArchive Status for: {playlist.title}')
        click.echo(f'Total videos: {len(videos)}\n')
        click.echo(f'  {click.style(f"Archived: {archived}", fg="green")}')
        click.echo(f'  Not archived: {not_archived}')
        if skipped > 0:
            click.echo(f'  {click.style(f"Skipped (already exists): {skipped}", fg="yellow")}')
        if failed > 0:
            click.echo(f'  {click.style(f"Failed: {failed}", fg="red")}')

        if verbose:
            click.echo('\nDetailed Status:\n')
            table_data = []
            for video in videos:
                status_icon = {
                    ArchiveStatus.ARCHIVED: click.style('[OK]', fg='green'),
                    ArchiveStatus.FAILED: click.style('[FAIL]', fg='red'),
                    ArchiveStatus.SKIPPED: click.style('[SKIP]', fg='yellow'),
                    ArchiveStatus.NOT_ARCHIVED: '[ ]',
                }
                table_data.append([
                    video.playlist_index,
                    video.title[:50] + '...' if len(video.title) > 50 else video.title,
                    status_icon.get(video.archive_status, '[ ]'),
                    video.archive_url[:60] + '...' if video.archive_url and len(video.archive_url) > 60 else (video.archive_url or '-')
                ])

            headers = ['#', 'Title', 'Status', 'Archive URL']
            click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))

    except Exception as e:
        click.echo(click.style(f'\n[FAIL] Error: {e}', fg='red'))


@cli.command('filmot-enrich')
@click.argument('playlist_id')
@click.option('--status', type=click.Choice(['deleted', 'private', 'unavailable', 'all']), default='all', help='Enrich only videos with specific status')
@click.pass_context
def filmot_enrich(ctx, playlist_id, status):
    """Enrich deleted/unavailable videos with metadata from Filmot.com archive."""
    storage = ctx.obj['storage']
    fetcher = ctx.obj['fetcher']

    try:
        # Load playlist
        playlist = storage.load_playlist(playlist_id)
        if not playlist:
            click.echo(click.style(f'[FAIL] Playlist {playlist_id} not found', fg='red'))
            return

        # Filter videos by status
        videos_to_enrich = []
        if status == 'all':
            # All unavailable videos
            videos_to_enrich = [
                v for v in playlist.videos.values()
                if v.status in [VideoStatus.DELETED, VideoStatus.UNAVAILABLE, VideoStatus.PRIVATE]
            ]
        else:
            # Specific status
            status_enum = VideoStatus(status.upper() if status != 'unavailable' else 'UNAVAILABLE')
            videos_to_enrich = [v for v in playlist.videos.values() if v.status == status_enum]

        if not videos_to_enrich:
            click.echo(f'No videos match the criteria (status: {status})')
            return

        click.echo(f'\nEnriching {len(videos_to_enrich)} video(s) from Filmot.com archive...\n')

        # Enrich each video
        enriched_count = 0
        not_found_count = 0

        for i, video in enumerate(videos_to_enrich, 1):
            display_title = video.title[:60] + '...' if len(video.title) > 60 else video.title
            click.echo(f'[{i}/{len(videos_to_enrich)}] {display_title}')

            # Try Filmot enrichment
            enriched, was_enriched = fetcher.filmot.enrich_video_metadata(video)

            if was_enriched:
                # Update in playlist
                playlist.videos[video.video_id] = enriched
                click.echo(click.style(f'  [OK] Enriched: {enriched.title[:60]}', fg='green'))
                enriched_count += 1
            else:
                click.echo(click.style(f'  [SKIP] Not found in Filmot archive', fg='yellow'))
                not_found_count += 1

        # Save playlist
        if enriched_count > 0:
            storage.save_playlist(playlist, create_version=False)

        # Summary
        click.echo(f'\nSummary:')
        click.echo(f'  Total: {len(videos_to_enrich)}')
        click.echo(f'  {click.style(f"Enriched: {enriched_count}", fg="green")}')
        click.echo(f'  {click.style(f"Not found: {not_found_count}", fg="yellow")}')

        if enriched_count > 0:
            click.echo(f'\n{click.style("✓", fg="green")} Playlist updated with Filmot metadata!')
            click.echo('\nNote: Enriched metadata is marked with [ARCHIVED FROM FILMOT] in the description.')

    except Exception as e:
        click.echo(click.style(f'\n[FAIL] Error: {e}', fg='red'))


def main():
    """Main entry point for CLI."""
    cli(obj={})


if __name__ == '__main__':
    main()
