"""Command-line interface for YouTube playlist downloader."""

import click
from pathlib import Path
from typing import Optional
from tabulate import tabulate

from ..core.auth import AuthManager
from ..core.playlist_fetcher import PlaylistFetcher
from ..core.storage import PlaylistStorage
from ..core.downloader import DownloadManager
from ..core.models import VideoStatus, DownloadStatus


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


@auth.command('status')
@click.pass_context
def auth_status(ctx):
    """Check authentication status."""
    auth_manager = ctx.obj['auth_manager']
    status = auth_manager.get_auth_status()

    click.echo('\nAuthentication Status:')
    click.echo(f"  Cookies: {click.style('✓ Available', fg='green') if status['cookies'] else click.style('✗ Not set', fg='red')}")
    click.echo(f"  OAuth:   {click.style('✓ Available', fg='green') if status['oauth'] else click.style('✗ Not set', fg='red')}")


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


def main():
    """Main entry point for CLI."""
    cli(obj={})


if __name__ == '__main__':
    main()
