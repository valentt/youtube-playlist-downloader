"""Storage module for JSON-based playlist versioning and persistence."""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import shutil

from .models import PlaylistMetadata, VideoMetadata, VideoStatus, PlaylistVersion


class PlaylistStorage:
    """Manages JSON storage and versioning for playlists."""

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize the storage manager.

        Args:
            base_dir: Base directory for storing playlists. Defaults to ./playlists
        """
        if base_dir is None:
            base_dir = Path.cwd() / 'playlists'

        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_playlist_dir(self, playlist_id: str) -> Path:
        """
        Get the directory for a specific playlist.

        Uses human-friendly folder name format: "Channel - PlaylistName"
        If playlist doesn't exist yet, creates folder with playlist_id temporarily.
        """
        # First try to find existing folder by searching current_state.json files
        for playlist_dir in self.base_dir.iterdir():
            if playlist_dir.is_dir():
                state_file = playlist_dir / 'current_state.json'
                if state_file.exists():
                    try:
                        with open(state_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if data.get('playlist_id') == playlist_id:
                                return playlist_dir
                    except Exception:
                        continue

        # Playlist not found - create new folder with playlist_id as temporary name
        # It will be renamed when saved with full metadata
        playlist_dir = self.base_dir / playlist_id
        playlist_dir.mkdir(parents=True, exist_ok=True)
        return playlist_dir

    def _get_human_friendly_folder_name(self, playlist: PlaylistMetadata) -> str:
        """
        Generate human-friendly folder name: "Channel - PlaylistName"

        Args:
            playlist: PlaylistMetadata object

        Returns:
            Sanitized folder name
        """
        from .downloader import sanitize_filename

        channel_name = playlist.channel or playlist.uploader or "Unknown Channel"
        safe_channel = sanitize_filename(channel_name)
        safe_title = sanitize_filename(playlist.title)

        return f"{safe_channel} - {safe_title}"

    def get_current_state_file(self, playlist_id: str) -> Path:
        """Get path to the current state JSON file."""
        return self.get_playlist_dir(playlist_id) / 'current_state.json'

    def get_history_file(self, playlist_id: str) -> Path:
        """Get path to the version history JSON file."""
        return self.get_playlist_dir(playlist_id) / 'version_history.json'

    def load_playlist(self, playlist_id: str) -> Optional[PlaylistMetadata]:
        """
        Load the current state of a playlist.

        Args:
            playlist_id: YouTube playlist ID

        Returns:
            PlaylistMetadata object or None if not found
        """
        state_file = self.get_current_state_file(playlist_id)

        if not state_file.exists():
            return None

        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return PlaylistMetadata.from_dict(data)
        except Exception as e:
            print(f"Error loading playlist {playlist_id}: {e}")
            return None

    def save_playlist(self, playlist: PlaylistMetadata, create_version: bool = True) -> None:
        """
        Save the current state of a playlist and optionally create a version snapshot.

        Args:
            playlist: PlaylistMetadata object to save
            create_version: If True, create a version snapshot in history
        """
        playlist_dir = self.get_playlist_dir(playlist.playlist_id)
        state_file = self.get_current_state_file(playlist.playlist_id)

        # Load previous state for comparison
        previous_playlist = self.load_playlist(playlist.playlist_id)

        # Update timestamp
        playlist.last_updated = datetime.now().isoformat()

        # Save current state
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(playlist.to_dict(), f, indent=2, ensure_ascii=False)

        # Create version snapshot if requested
        if create_version:
            self._create_version_snapshot(playlist, previous_playlist)

        # Rename folder to human-friendly name if needed
        new_folder_name = self._get_human_friendly_folder_name(playlist)
        new_playlist_dir = self.base_dir / new_folder_name

        # Only rename if the name is different and new name doesn't exist
        if playlist_dir.name != new_folder_name:
            if not new_playlist_dir.exists():
                try:
                    playlist_dir.rename(new_playlist_dir)
                    print(f"Playlist saved and renamed to: {new_folder_name}")
                except Exception as e:
                    print(f"Playlist saved: {state_file} (Could not rename folder: {e})")
            else:
                # Target folder exists - could be a naming collision
                # Check if it's the same playlist
                try:
                    with open(new_playlist_dir / 'current_state.json', 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        if existing_data.get('playlist_id') == playlist.playlist_id:
                            # Same playlist, remove old folder and keep the new one
                            shutil.rmtree(playlist_dir)
                            print(f"Playlist saved: {new_playlist_dir / 'current_state.json'}")
                        else:
                            # Different playlist with same name - keep old folder name
                            print(f"Playlist saved: {state_file} (Folder name collision prevented)")
                except Exception as e:
                    print(f"Playlist saved: {state_file} (Error handling folder rename: {e})")
        else:
            print(f"Playlist saved: {state_file}")

    def _create_version_snapshot(
        self,
        current: PlaylistMetadata,
        previous: Optional[PlaylistMetadata]
    ) -> None:
        """
        Create a version snapshot by comparing current and previous states.

        Args:
            current: Current playlist state
            previous: Previous playlist state (or None if first save)
        """
        history_file = self.get_history_file(current.playlist_id)

        # Load existing history
        history = self._load_history(current.playlist_id)

        # Calculate version number
        version = len(history) + 1

        # Detect changes
        videos_added = []
        videos_removed = []
        videos_status_changed = []

        if previous is None:
            # First version - all videos are new
            videos_added = list(current.videos.keys())
        else:
            # Compare with previous state
            current_ids = set(current.videos.keys())
            previous_ids = set(previous.videos.keys())

            # Detect added videos
            videos_added = list(current_ids - previous_ids)

            # Detect removed videos (though we keep them in current state with status)
            videos_removed = list(previous_ids - current_ids)

            # Detect status changes
            for video_id in current_ids & previous_ids:
                curr_video = current.videos[video_id]
                prev_video = previous.videos[video_id]

                if curr_video.status != prev_video.status:
                    videos_status_changed.append({
                        'video_id': video_id,
                        'title': curr_video.title,
                        'old_status': prev_video.status.value,
                        'new_status': curr_video.status.value,
                    })

        # Only create a version if there are actual changes
        if videos_added or videos_removed or videos_status_changed:
            version_snapshot = PlaylistVersion(
                version=version,
                timestamp=datetime.now().isoformat(),
                videos_added=videos_added,
                videos_removed=videos_removed,
                videos_status_changed=videos_status_changed,
                note=f"Playlist update: {len(videos_added)} added, "
                     f"{len(videos_status_changed)} status changed"
            )

            history.append(version_snapshot.to_dict())

            # Save updated history
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

            print(f"Version {version} created: {len(videos_added)} added, "
                  f"{len(videos_status_changed)} status changed")

    def _load_history(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Load version history for a playlist."""
        history_file = self.get_history_file(playlist_id)

        if not history_file.exists():
            return []

        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading history for {playlist_id}: {e}")
            return []

    def get_history(self, playlist_id: str) -> List[PlaylistVersion]:
        """
        Get version history for a playlist.

        Args:
            playlist_id: YouTube playlist ID

        Returns:
            List of PlaylistVersion objects
        """
        history_data = self._load_history(playlist_id)
        return [PlaylistVersion.from_dict(v) for v in history_data]

    def update_playlist(
        self,
        new_playlist: PlaylistMetadata,
        existing_playlist: Optional[PlaylistMetadata] = None
    ) -> PlaylistMetadata:
        """
        Update a playlist by merging new data with existing data.

        This preserves historical information and updates status as needed.

        Args:
            new_playlist: Newly fetched playlist data
            existing_playlist: Existing playlist data (if None, loads from storage)

        Returns:
            Updated PlaylistMetadata
        """
        if existing_playlist is None:
            existing_playlist = self.load_playlist(new_playlist.playlist_id)

        # If no existing data, just return the new playlist
        if existing_playlist is None:
            return new_playlist

        # Merge videos
        merged_videos = {}

        # Start with existing videos
        for video_id, video in existing_playlist.videos.items():
            if video_id in new_playlist.videos:
                # Video still exists - update it
                new_video = new_playlist.videos[video_id]

                # Preserve history
                new_video.status_history = video.status_history
                new_video.first_seen = video.first_seen

                # Check if status changed
                if new_video.status != video.status:
                    new_video.update_status(new_video.status, "Status detected during update")

                # Preserve download information
                new_video.download_status = video.download_status
                new_video.video_path = video.video_path
                new_video.audio_path = video.audio_path

                merged_videos[video_id] = new_video
            else:
                # Video no longer in playlist - mark as deleted/unavailable
                if video.status == VideoStatus.LIVE:
                    video.update_status(VideoStatus.DELETED, "Video no longer in playlist")
                video.last_checked = datetime.now().isoformat()
                merged_videos[video_id] = video

        # Add new videos
        for video_id, video in new_playlist.videos.items():
            if video_id not in merged_videos:
                merged_videos[video_id] = video

        # Update playlist metadata
        existing_playlist.title = new_playlist.title
        existing_playlist.description = new_playlist.description
        existing_playlist.channel = new_playlist.channel
        existing_playlist.channel_id = new_playlist.channel_id
        existing_playlist.uploader = new_playlist.uploader
        existing_playlist.webpage_url = new_playlist.webpage_url
        existing_playlist.video_count = len(merged_videos)
        existing_playlist.videos = merged_videos
        existing_playlist.last_updated = datetime.now().isoformat()

        return existing_playlist

    def list_playlists(self) -> List[Dict[str, str]]:
        """
        List all stored playlists.

        Returns:
            List of dictionaries with playlist_id, title, channel, and last_updated
        """
        playlists = []

        for playlist_dir in self.base_dir.iterdir():
            if playlist_dir.is_dir():
                state_file = playlist_dir / 'current_state.json'
                if state_file.exists():
                    try:
                        with open(state_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            playlists.append({
                                'playlist_id': data.get('playlist_id', ''),
                                'title': data.get('title', 'Unknown'),
                                'channel': data.get('channel') or data.get('uploader', 'Unknown'),
                                'last_updated': data.get('last_updated', ''),
                                'video_count': len(data.get('videos', {})),
                            })
                    except Exception:
                        pass

        return playlists

    def export_playlist(self, playlist_id: str, output_file: Path) -> None:
        """
        Export a playlist to a standalone JSON file.

        Args:
            playlist_id: YouTube playlist ID
            output_file: Path to output JSON file
        """
        playlist = self.load_playlist(playlist_id)
        if playlist is None:
            raise ValueError(f"Playlist {playlist_id} not found")

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(playlist.to_dict(), f, indent=2, ensure_ascii=False)

        print(f"Playlist exported to: {output_file}")

    def delete_playlist(self, playlist_id: str) -> bool:
        """
        Delete a playlist and all its associated data.

        Args:
            playlist_id: YouTube playlist ID

        Returns:
            True if successful, False otherwise
        """
        playlist_dir = self.get_playlist_dir(playlist_id)

        if not playlist_dir.exists():
            print(f"Playlist {playlist_id} not found")
            return False

        try:
            # Delete the entire playlist directory
            shutil.rmtree(playlist_dir)
            print(f"Playlist deleted: {playlist_id}")
            return True
        except Exception as e:
            print(f"Error deleting playlist {playlist_id}: {e}")
            return False

    def migrate_to_human_friendly_names(self) -> None:
        """
        Migrate all existing playlist folders to human-friendly names.

        Renames folders from playlist IDs to "Channel - PlaylistName" format.
        """
        print("\n=== Migrating Playlist Folders to Human-Friendly Names ===\n")

        migrated_count = 0
        error_count = 0

        for playlist_dir in self.base_dir.iterdir():
            if not playlist_dir.is_dir():
                continue

            state_file = playlist_dir / 'current_state.json'
            if not state_file.exists():
                continue

            try:
                # Load playlist data
                with open(state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                playlist = PlaylistMetadata.from_dict(data)

                # Get new folder name
                new_folder_name = self._get_human_friendly_folder_name(playlist)
                new_playlist_dir = self.base_dir / new_folder_name

                # Check if rename is needed
                if playlist_dir.name == new_folder_name:
                    print(f"[OK] Already migrated: {new_folder_name}")
                    continue

                # Check if target exists
                if new_playlist_dir.exists():
                    # Check if it's the same playlist
                    try:
                        with open(new_playlist_dir / 'current_state.json', 'r', encoding='utf-8') as f:
                            existing_data = json.load(f)
                            if existing_data.get('playlist_id') == playlist.playlist_id:
                                # Same playlist, remove old folder
                                shutil.rmtree(playlist_dir)
                                print(f"[OK] Merged duplicate: {playlist_dir.name} -> {new_folder_name}")
                                migrated_count += 1
                                continue
                            else:
                                print(f"[ERROR] Naming collision: {playlist_dir.name} conflicts with {new_folder_name}")
                                error_count += 1
                                continue
                    except Exception as e:
                        print(f"[ERROR] Error checking existing folder {new_folder_name}: {e}")
                        error_count += 1
                        continue

                # Rename folder
                playlist_dir.rename(new_playlist_dir)
                print(f"[OK] Migrated: {playlist_dir.name} -> {new_folder_name}")
                migrated_count += 1

            except Exception as e:
                print(f"[ERROR] Error migrating {playlist_dir.name}: {e}")
                error_count += 1

        print(f"\n=== Migration Complete ===")
        print(f"Migrated: {migrated_count}")
        print(f"Errors: {error_count}")
        print()
