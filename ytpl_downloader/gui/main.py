"""Graphical user interface for YouTube playlist downloader."""

import sys
import webbrowser
from pathlib import Path
from typing import Optional, List
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QTableWidget, QTableWidgetItem,
    QComboBox, QSpinBox, QCheckBox, QTabWidget, QTextEdit,
    QFileDialog, QMessageBox, QProgressBar, QHeaderView, QGroupBox,
    QRadioButton, QMenu
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor

from ..core.auth import AuthManager
from ..core.playlist_fetcher import PlaylistFetcher
from ..core.storage import PlaylistStorage
from ..core.downloader import DownloadManager
from ..core.models import PlaylistMetadata, VideoStatus, DownloadStatus


class FetchThread(QThread):
    """Background thread for fetching playlists."""
    finished = Signal(object)  # PlaylistMetadata
    error = Signal(str)
    progress = Signal(int, int, str)  # current, total, message

    def __init__(self, fetcher: PlaylistFetcher, url: str, fast_mode: bool = False):
        super().__init__()
        self.fetcher = fetcher
        self.url = url
        self.fast_mode = fast_mode

    def run(self):
        try:
            def progress_callback(current, total, message):
                self.progress.emit(current, total, message)

            playlist = self.fetcher.fetch_playlist(
                self.url,
                quiet=False,
                progress_callback=progress_callback,
                fast_mode=self.fast_mode
            )
            self.finished.emit(playlist)
        except Exception as e:
            self.error.emit(str(e))


class DownloadThread(QThread):
    """Background thread for downloading playlists."""
    finished = Signal(dict)  # results
    error = Signal(str)
    progress = Signal(str)  # status message

    def __init__(self, downloader: DownloadManager, storage: PlaylistStorage,
                 playlist: PlaylistMetadata, quality: str, download_video: bool,
                 download_audio: bool, download_comments: bool, workers: int):
        super().__init__()
        self.downloader = downloader
        self.storage = storage
        self.playlist = playlist
        self.quality = quality
        self.download_video = download_video
        self.download_audio = download_audio
        self.download_comments = download_comments
        self.workers = workers

    def run(self):
        try:
            output_dir = self.downloader.get_playlist_download_dir(self.playlist)
            results = {}

            # Download videos if requested
            if self.download_video:
                video_results = self.downloader.download_playlist(
                    self.playlist,
                    quality=self.quality,
                    audio_only=False,
                    download_metadata_only=False,
                    max_workers=self.workers
                )
                results.update(video_results)

            # Download audio if requested
            if self.download_audio:
                audio_results = self.downloader.download_playlist(
                    self.playlist,
                    quality=self.quality,
                    audio_only=True,
                    download_metadata_only=False,
                    max_workers=self.workers
                )
                # Merge results (keep track of what was downloaded)
                for vid_id, success in audio_results.items():
                    if vid_id in results:
                        results[vid_id] = results[vid_id] and success
                    else:
                        results[vid_id] = success

            # Download comments if requested
            if self.download_comments:
                for video in self.playlist.videos.values():
                    if video.status == VideoStatus.LIVE:
                        self.downloader.download_comments(video, output_dir)
                # Save playlist with updated comments paths
                self.storage.save_playlist(self.playlist, create_version=False)

            # If nothing was downloaded (only metadata update)
            if not self.download_video and not self.download_audio and not self.download_comments:
                self.storage.update_playlist(self.playlist)
                self.storage.save_playlist(self.playlist)

            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class EnrichThread(QThread):
    """Background thread for enriching playlist metadata."""
    finished = Signal(object)  # PlaylistMetadata
    error = Signal(str)
    progress = Signal(int, int, str)  # current, total, message

    def __init__(self, fetcher: PlaylistFetcher, playlist: PlaylistMetadata):
        super().__init__()
        self.fetcher = fetcher
        self.playlist = playlist

    def run(self):
        try:
            def progress_callback(current, total, message):
                self.progress.emit(current, total, message)

            enriched = self.fetcher.enrich_playlist_metadata(
                self.playlist,
                progress_callback=progress_callback
            )
            self.finished.emit(enriched)
        except Exception as e:
            self.error.emit(str(e))


class SingleVideoDownloadThread(QThread):
    """Background thread for downloading a single video."""
    finished = Signal(bool)  # success
    error = Signal(str)
    progress = Signal(str)  # status message

    def __init__(self, downloader: DownloadManager, storage: PlaylistStorage,
                 playlist: PlaylistMetadata, video_id: str, quality: str, audio_only: bool,
                 download_comments: bool = False):
        super().__init__()
        self.downloader = downloader
        self.storage = storage
        self.playlist = playlist
        self.video_id = video_id
        self.quality = quality
        self.audio_only = audio_only
        self.download_comments = download_comments

    def run(self):
        try:
            # Download just this one video
            video = self.playlist.videos.get(self.video_id)
            if not video:
                self.error.emit(f"Video {self.video_id} not found in playlist")
                return

            self.progress.emit(f"Downloading: {video.title}")

            # Get the output directory for this playlist
            output_dir = self.downloader.get_playlist_download_dir(self.playlist)

            # Download the video
            success = self.downloader.download_video(
                video,
                output_dir,
                quality=self.quality,
                audio_only=self.audio_only
            )

            # Download comments if requested
            if success and self.download_comments:
                self.downloader.download_comments(video, output_dir)

            # Save the playlist to persist download status
            if success:
                self.storage.save_playlist(self.playlist, create_version=False)

            self.finished.emit(success)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Playlist Downloader")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize managers
        self.auth_manager = AuthManager()
        self.storage = PlaylistStorage()
        self.fetcher = PlaylistFetcher(self.auth_manager)
        self.downloader = DownloadManager(self.auth_manager, self.storage)

        # Current playlist
        self.current_playlist: Optional[PlaylistMetadata] = None

        # Setup UI
        self.setup_ui()

        # Load playlists list
        self.refresh_playlists_list()

    def setup_ui(self):
        """Set up the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # Create tabs
        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # Tab 1: Playlists
        self.playlist_tab = self.create_playlist_tab()
        tabs.addTab(self.playlist_tab, "Playlists")

        # Tab 2: Videos
        self.videos_tab = self.create_videos_tab()
        tabs.addTab(self.videos_tab, "Videos")

        # Tab 3: Settings
        self.settings_tab = self.create_settings_tab()
        tabs.addTab(self.settings_tab, "Settings")

        # Status bar
        self.statusBar().showMessage("Ready")

    def create_playlist_tab(self) -> QWidget:
        """Create the playlists tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Fetch section
        fetch_group = QGroupBox("Fetch Playlist")
        fetch_layout = QVBoxLayout(fetch_group)

        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Playlist URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/playlist?list=...")
        url_layout.addWidget(self.url_input)

        self.fetch_button = QPushButton("Fetch")
        self.fetch_button.clicked.connect(self.fetch_playlist)
        url_layout.addWidget(self.fetch_button)

        fetch_layout.addLayout(url_layout)

        # Fetch mode selection
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Fetch Mode:"))
        self.fast_mode_radio = QRadioButton("Fast (~30s) - Basic info only")
        self.detailed_mode_radio = QRadioButton("Detailed (~5-10min) - Full metadata + error messages")
        self.detailed_mode_radio.setChecked(True)  # Default to detailed
        mode_layout.addWidget(self.fast_mode_radio)
        mode_layout.addWidget(self.detailed_mode_radio)
        mode_layout.addStretch()
        fetch_layout.addLayout(mode_layout)

        # Progress bar for fetching
        self.fetch_progress_bar = QProgressBar()
        self.fetch_progress_bar.setVisible(False)
        self.fetch_progress_label = QLabel()
        self.fetch_progress_label.setVisible(False)
        fetch_layout.addWidget(self.fetch_progress_bar)
        fetch_layout.addWidget(self.fetch_progress_label)

        layout.addWidget(fetch_group)

        # Playlists list
        playlists_group = QGroupBox("Stored Playlists")
        playlists_layout = QVBoxLayout(playlists_group)

        self.playlists_table = QTableWidget()
        self.playlists_table.setColumnCount(4)
        self.playlists_table.setHorizontalHeaderLabels(["Channel", "Title", "Videos", "Last Updated"])
        self.playlists_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.playlists_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.playlists_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.playlists_table.customContextMenuRequested.connect(self.show_playlist_context_menu)
        self.playlists_table.itemSelectionChanged.connect(self.on_playlist_selected)
        playlists_layout.addWidget(self.playlists_table)

        buttons_layout = QHBoxLayout()
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_playlists_list)
        buttons_layout.addWidget(refresh_button)

        self.load_button = QPushButton("Load Selected")
        self.load_button.clicked.connect(self.load_selected_playlist)
        buttons_layout.addWidget(self.load_button)

        update_button = QPushButton("Update Selected")
        update_button.clicked.connect(self.update_selected_playlist)
        buttons_layout.addWidget(update_button)

        buttons_layout.addStretch()
        playlists_layout.addLayout(buttons_layout)

        layout.addWidget(playlists_group)

        return tab

    def create_videos_tab(self) -> QWidget:
        """Create the videos tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Current playlist info
        self.playlist_info_label = QLabel("No playlist loaded")
        self.playlist_info_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.playlist_info_label)

        # Filters
        filter_group = QGroupBox("Filters")
        filter_layout = QHBoxLayout(filter_group)

        filter_layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Live", "Deleted", "Private", "Unavailable"])
        self.status_filter.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.status_filter)

        filter_layout.addWidget(QLabel("Downloaded:"))
        self.download_filter = QComboBox()
        self.download_filter.addItems(["All", "Yes", "No"])
        self.download_filter.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.download_filter)

        filter_layout.addStretch()
        layout.addWidget(filter_group)

        # Videos table
        self.videos_table = QTableWidget()
        self.videos_table.setColumnCount(8)
        self.videos_table.setHorizontalHeaderLabels(["#", "Video ID", "Title", "Channel", "Status", "Video DL", "Audio DL", "Comments"])
        self.videos_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.videos_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.videos_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.videos_table.customContextMenuRequested.connect(self.show_video_context_menu)
        layout.addWidget(self.videos_table)

        # Download controls
        download_group = QGroupBox("Download Options")
        download_layout = QVBoxLayout(download_group)

        # Metadata enrichment
        enrich_layout = QHBoxLayout()
        self.enrich_button = QPushButton("Get Detailed Metadata for Entire Playlist")
        self.enrich_button.clicked.connect(self.enrich_playlist)
        self.enrich_button.setEnabled(False)
        self.enrich_button.setToolTip("Upgrade a fast-fetched playlist to have detailed metadata including error messages")
        enrich_layout.addWidget(self.enrich_button)
        enrich_layout.addStretch()
        download_layout.addLayout(enrich_layout)

        # Enrich progress bar
        self.enrich_progress_bar = QProgressBar()
        self.enrich_progress_bar.setVisible(False)
        self.enrich_progress_label = QLabel()
        self.enrich_progress_label.setVisible(False)
        download_layout.addWidget(self.enrich_progress_bar)
        download_layout.addWidget(self.enrich_progress_label)

        # Quality and options
        options_layout = QHBoxLayout()

        options_layout.addWidget(QLabel("Quality:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["1080p", "720p", "best"])
        options_layout.addWidget(self.quality_combo)

        options_layout.addWidget(QLabel("Download:"))
        self.download_video_checkbox = QCheckBox("Video")
        self.download_video_checkbox.setChecked(True)  # Default to video
        options_layout.addWidget(self.download_video_checkbox)

        self.download_audio_checkbox = QCheckBox("Audio")
        options_layout.addWidget(self.download_audio_checkbox)

        self.download_comments_checkbox = QCheckBox("Comments")
        self.download_comments_checkbox.setToolTip("Download all comments to markdown files")
        options_layout.addWidget(self.download_comments_checkbox)

        options_layout.addWidget(QLabel("Workers:"))
        self.workers_spinbox = QSpinBox()
        self.workers_spinbox.setRange(1, 20)
        self.workers_spinbox.setValue(5)
        options_layout.addWidget(self.workers_spinbox)

        options_layout.addStretch()
        download_layout.addLayout(options_layout)

        # Download button
        self.download_button = QPushButton("Download Playlist")
        self.download_button.clicked.connect(self.download_playlist)
        self.download_button.setEnabled(False)
        download_layout.addWidget(self.download_button)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        download_layout.addWidget(self.progress_bar)

        layout.addWidget(download_group)

        return tab

    def create_settings_tab(self) -> QWidget:
        """Create the settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Authentication section
        auth_group = QGroupBox("Authentication")
        auth_layout = QVBoxLayout(auth_group)

        # Cookies
        cookies_layout = QHBoxLayout()
        cookies_layout.addWidget(QLabel("Cookies File:"))
        self.cookies_path_label = QLabel("Not set")
        cookies_layout.addWidget(self.cookies_path_label)
        cookies_button = QPushButton("Set Cookies")
        cookies_button.clicked.connect(self.set_cookies)
        cookies_layout.addWidget(cookies_button)
        cookies_layout.addStretch()
        auth_layout.addLayout(cookies_layout)

        # OAuth
        oauth_layout = QHBoxLayout()
        oauth_layout.addWidget(QLabel("OAuth:"))
        self.oauth_status_label = QLabel("Not configured")
        oauth_layout.addWidget(self.oauth_status_label)
        oauth_button = QPushButton("Setup OAuth")
        oauth_button.clicked.connect(self.setup_oauth)
        oauth_layout.addWidget(oauth_button)
        oauth_layout.addStretch()
        auth_layout.addLayout(oauth_layout)

        layout.addWidget(auth_group)

        # Update auth status
        self.update_auth_status()

        # Log section
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)

        return tab

    def fetch_playlist(self):
        """Fetch a playlist from URL."""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a playlist URL")
            return

        # Get fetch mode from radio buttons
        fast_mode = self.fast_mode_radio.isChecked()
        mode_str = "fast" if fast_mode else "detailed"

        self.fetch_button.setEnabled(False)
        self.fetch_progress_bar.setVisible(True)
        self.fetch_progress_label.setVisible(True)
        self.fetch_progress_bar.setMaximum(100)
        self.fetch_progress_bar.setValue(0)
        self.fetch_progress_label.setText("Starting...")
        self.statusBar().showMessage(f"Fetching playlist ({mode_str} mode)...")
        self.log(f"Fetching playlist ({mode_str} mode): " + url)

        # Create and start fetch thread
        self.fetch_thread = FetchThread(self.fetcher, url, fast_mode)
        self.fetch_thread.finished.connect(self.on_fetch_finished)
        self.fetch_thread.error.connect(self.on_fetch_error)
        self.fetch_thread.progress.connect(self.on_fetch_progress)
        self.fetch_thread.start()

    def on_fetch_progress(self, current: int, total: int, message: str):
        """Handle fetch progress updates."""
        if total > 0:
            percentage = int((current / total) * 100)
            self.fetch_progress_bar.setValue(percentage)
            self.fetch_progress_label.setText(message)
            self.statusBar().showMessage(message)

    def on_fetch_finished(self, playlist: PlaylistMetadata):
        """Handle successful playlist fetch."""
        self.fetch_button.setEnabled(True)
        self.fetch_progress_bar.setVisible(False)
        self.fetch_progress_label.setVisible(False)

        # Update with existing data
        updated = self.storage.update_playlist(playlist)
        self.storage.save_playlist(updated)

        self.log(f"Playlist fetched: {updated.title} ({len(updated.videos)} videos)")
        self.statusBar().showMessage("Playlist fetched successfully")

        # Load the playlist
        self.current_playlist = updated
        self.display_playlist()
        self.refresh_playlists_list()

        QMessageBox.information(self, "Success", f"Playlist fetched successfully!\n\n{updated.title}\n{len(updated.videos)} videos")

    def on_fetch_error(self, error: str):
        """Handle fetch error."""
        self.fetch_button.setEnabled(True)
        self.fetch_progress_bar.setVisible(False)
        self.fetch_progress_label.setVisible(False)
        self.log(f"Error fetching playlist: {error}")
        self.statusBar().showMessage("Error fetching playlist")
        QMessageBox.critical(self, "Error", f"Failed to fetch playlist:\n{error}")

    def refresh_playlists_list(self):
        """Refresh the playlists list."""
        playlists = self.storage.list_playlists()
        self.playlists_table.setRowCount(len(playlists))

        for row, playlist in enumerate(playlists):
            # Column 0: Channel (with playlist_id stored as user data)
            channel_item = QTableWidgetItem(playlist.get('channel', 'Unknown'))
            channel_item.setData(Qt.UserRole, playlist['playlist_id'])  # Store playlist_id
            self.playlists_table.setItem(row, 0, channel_item)

            # Column 1: Title
            self.playlists_table.setItem(row, 1, QTableWidgetItem(playlist['title']))

            # Column 2: Video count
            self.playlists_table.setItem(row, 2, QTableWidgetItem(str(playlist['video_count'])))

            # Column 3: Last updated
            self.playlists_table.setItem(row, 3, QTableWidgetItem(playlist['last_updated'][:19]))

    def on_playlist_selected(self):
        """Handle playlist selection."""
        pass  # Selection handled, load button will use it

    def load_selected_playlist(self):
        """Load the selected playlist."""
        selected = self.playlists_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Error", "Please select a playlist")
            return

        row = selected[0].row()
        # Get playlist_id from user data (stored in column 0)
        playlist_id = self.playlists_table.item(row, 0).data(Qt.UserRole)

        playlist = self.storage.load_playlist(playlist_id)
        if playlist:
            self.current_playlist = playlist
            self.display_playlist()
            self.log(f"Loaded playlist: {playlist.title}")
        else:
            QMessageBox.critical(self, "Error", "Failed to load playlist")

    def update_selected_playlist(self):
        """Update the selected playlist by re-fetching."""
        selected = self.playlists_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Error", "Please select a playlist")
            return

        row = selected[0].row()
        # Get playlist_id from user data (stored in column 0)
        playlist_id = self.playlists_table.item(row, 0).data(Qt.UserRole)

        playlist = self.storage.load_playlist(playlist_id)
        if not playlist:
            QMessageBox.critical(self, "Error", "Failed to load playlist")
            return

        # Use the webpage_url to re-fetch
        self.url_input.setText(playlist.webpage_url)
        self.fetch_playlist()

    def show_playlist_context_menu(self, position):
        """Show context menu for playlist table."""
        # Get the clicked row
        item = self.playlists_table.itemAt(position)
        if not item:
            return

        row = item.row()
        playlist_id = self.playlists_table.item(row, 0).data(Qt.UserRole)
        playlist_title = self.playlists_table.item(row, 1).text()

        if not playlist_id:
            return

        # Load playlist to get webpage_url
        playlist = self.storage.load_playlist(playlist_id)
        if not playlist:
            return

        # Create context menu
        menu = QMenu(self)

        # Open URL action
        open_url_action = menu.addAction("Open Playlist URL in Browser")
        menu.addSeparator()

        # Delete action
        delete_action = menu.addAction("Delete Playlist")

        # Show menu and handle action
        action = menu.exec_(self.playlists_table.viewport().mapToGlobal(position))

        if action == open_url_action:
            self.open_playlist_url(playlist)
        elif action == delete_action:
            self.delete_playlist(playlist_id, playlist_title)

    def open_playlist_url(self, playlist: PlaylistMetadata):
        """Open playlist URL in external browser."""
        if not playlist.webpage_url:
            QMessageBox.warning(
                self,
                "No URL",
                "This playlist doesn't have a URL stored."
            )
            return

        try:
            webbrowser.open(playlist.webpage_url)
            self.log(f"Opened playlist URL: {playlist.title}")
            self.statusBar().showMessage("Opened playlist in browser")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open URL in browser:\n{str(e)}"
            )

    def delete_playlist(self, playlist_id: str, playlist_title: str):
        """Delete a playlist after confirmation."""
        reply = QMessageBox.question(
            self,
            "Delete Playlist",
            f"Are you sure you want to delete this playlist?\n\n{playlist_title}\n\n"
            f"This will permanently delete all metadata and version history.\n"
            f"Downloaded files will NOT be deleted.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Delete the playlist
        success = self.storage.delete_playlist(playlist_id)

        if success:
            self.log(f"Deleted playlist: {playlist_title}")
            self.statusBar().showMessage("Playlist deleted")

            # If this was the current playlist, clear it
            if self.current_playlist and self.current_playlist.playlist_id == playlist_id:
                self.current_playlist = None
                self.display_playlist()

            # Refresh the playlists list
            self.refresh_playlists_list()

            QMessageBox.information(
                self,
                "Success",
                f"Playlist deleted successfully:\n{playlist_title}"
            )
        else:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to delete playlist:\n{playlist_title}"
            )

    def display_playlist(self):
        """Display the current playlist in the videos tab."""
        if not self.current_playlist:
            return

        self.playlist_info_label.setText(
            f"Playlist: {self.current_playlist.title} ({len(self.current_playlist.videos)} videos)"
        )
        self.download_button.setEnabled(True)
        self.enrich_button.setEnabled(True)

        # Apply filters and display
        self.apply_filters()

    def apply_filters(self):
        """Apply filters and display videos."""
        if not self.current_playlist:
            self.videos_table.setRowCount(0)
            return

        # Get filter values
        status_filter = self.status_filter.currentText().lower()
        download_filter = self.download_filter.currentText().lower()

        # Filter videos
        videos = list(self.current_playlist.videos.values())

        if status_filter != "all":
            status_map = {
                "live": VideoStatus.LIVE,
                "deleted": VideoStatus.DELETED,
                "private": VideoStatus.PRIVATE,
                "unavailable": VideoStatus.UNAVAILABLE,
            }
            videos = [v for v in videos if v.status == status_map[status_filter]]

        if download_filter == "yes":
            videos = [v for v in videos if v.download_status == DownloadStatus.COMPLETED]
        elif download_filter == "no":
            videos = [v for v in videos if v.download_status != DownloadStatus.COMPLETED]

        # Sort by index
        videos.sort(key=lambda v: v.playlist_index)

        # Display in table
        self.videos_table.setRowCount(len(videos))

        for row, video in enumerate(videos):
            # Store video_id in first column as user data for context menu
            index_item = QTableWidgetItem(str(video.playlist_index))
            index_item.setData(Qt.UserRole, video.video_id)
            self.videos_table.setItem(row, 0, index_item)

            self.videos_table.setItem(row, 1, QTableWidgetItem(video.video_id))

            title_item = QTableWidgetItem(video.title)
            self.videos_table.setItem(row, 2, title_item)

            self.videos_table.setItem(row, 3, QTableWidgetItem(video.channel))

            status_item = QTableWidgetItem(video.status.value)
            # Color code status
            if video.status == VideoStatus.LIVE:
                status_item.setForeground(QColor("green"))
            elif video.status == VideoStatus.DELETED:
                status_item.setForeground(QColor("red"))
            elif video.status == VideoStatus.PRIVATE:
                status_item.setForeground(QColor("orange"))
            else:
                status_item.setForeground(QColor("gray"))
            self.videos_table.setItem(row, 4, status_item)

            # Video download status
            video_dl_item = QTableWidgetItem("✓" if video.video_path else "✗")
            if video.video_path:
                video_dl_item.setForeground(QColor("green"))
            self.videos_table.setItem(row, 5, video_dl_item)

            # Audio download status
            audio_dl_item = QTableWidgetItem("✓" if video.audio_path else "✗")
            if video.audio_path:
                audio_dl_item.setForeground(QColor("green"))
            self.videos_table.setItem(row, 6, audio_dl_item)

            # Comments download status
            comments_dl_item = QTableWidgetItem("✓" if video.comments_path else "✗")
            if video.comments_path:
                comments_dl_item.setForeground(QColor("green"))
            self.videos_table.setItem(row, 7, comments_dl_item)

    def download_playlist(self):
        """Download the current playlist."""
        if not self.current_playlist:
            return

        quality = self.quality_combo.currentText()
        download_video = self.download_video_checkbox.isChecked()
        download_audio = self.download_audio_checkbox.isChecked()
        download_comments = self.download_comments_checkbox.isChecked()
        workers = self.workers_spinbox.value()

        # Validate that at least one option is selected
        if not download_video and not download_audio and not download_comments:
            QMessageBox.warning(
                self,
                "No Download Options Selected",
                "Please select at least one download option (Video, Audio, or Comments)"
            )
            return

        self.download_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(0)  # Indeterminate
        self.statusBar().showMessage("Downloading...")
        self.log(f"Starting download: {self.current_playlist.title}")

        # Create and start download thread
        self.download_thread = DownloadThread(
            self.downloader, self.storage, self.current_playlist,
            quality, download_video, download_audio, download_comments, workers
        )
        self.download_thread.finished.connect(self.on_download_finished)
        self.download_thread.error.connect(self.on_download_error)
        self.download_thread.start()

    def on_download_finished(self, results: dict):
        """Handle successful download."""
        self.download_button.setEnabled(True)
        self.progress_bar.setVisible(False)

        if results:
            successful = sum(1 for success in results.values() if success)
            self.log(f"Download complete: {successful}/{len(results)} items successful")
            self.statusBar().showMessage("Download complete")
            QMessageBox.information(self, "Success", f"Download complete!\n{successful}/{len(results)} items successful")
        else:
            # This happens when only comments were downloaded (no video/audio)
            self.log("Download complete (comments only)")
            self.statusBar().showMessage("Download complete")
            QMessageBox.information(self, "Success", "Download complete!")

        # Refresh display
        self.display_playlist()

    def on_download_error(self, error: str):
        """Handle download error."""
        self.download_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.log(f"Download error: {error}")
        self.statusBar().showMessage("Download failed")
        QMessageBox.critical(self, "Error", f"Download failed:\n{error}")

    def enrich_playlist(self):
        """Enrich the current playlist with detailed metadata."""
        if not self.current_playlist:
            return

        reply = QMessageBox.question(
            self,
            "Enrich Metadata",
            f"This will fetch detailed metadata for all {len(self.current_playlist.videos)} videos.\n\n"
            "This may take 5-10 minutes for large playlists.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        self.enrich_button.setEnabled(False)
        self.enrich_progress_bar.setVisible(True)
        self.enrich_progress_label.setVisible(True)
        self.enrich_progress_bar.setMaximum(100)
        self.enrich_progress_bar.setValue(0)
        self.enrich_progress_label.setText("Starting enrichment...")
        self.statusBar().showMessage("Enriching playlist metadata...")
        self.log(f"Enriching playlist: {self.current_playlist.title}")

        # Create and start enrich thread
        self.enrich_thread = EnrichThread(self.fetcher, self.current_playlist)
        self.enrich_thread.finished.connect(self.on_enrich_finished)
        self.enrich_thread.error.connect(self.on_enrich_error)
        self.enrich_thread.progress.connect(self.on_enrich_progress)
        self.enrich_thread.start()

    def on_enrich_progress(self, current: int, total: int, message: str):
        """Handle enrichment progress updates."""
        if total > 0:
            percentage = int((current / total) * 100)
            self.enrich_progress_bar.setValue(percentage)
            self.enrich_progress_label.setText(message)
            self.statusBar().showMessage(message)

    def on_enrich_finished(self, enriched_playlist: PlaylistMetadata):
        """Handle successful enrichment."""
        self.enrich_button.setEnabled(True)
        self.enrich_progress_bar.setVisible(False)
        self.enrich_progress_label.setVisible(False)

        # Save the enriched playlist
        self.storage.save_playlist(enriched_playlist, create_version=False)
        self.current_playlist = enriched_playlist

        self.log(f"Playlist enriched: {enriched_playlist.title}")
        self.statusBar().showMessage("Playlist enriched successfully")

        # Refresh display
        self.display_playlist()

        QMessageBox.information(
            self,
            "Success",
            f"Playlist enriched successfully!\n\nDetailed metadata fetched for {len(enriched_playlist.videos)} videos."
        )

    def on_enrich_error(self, error: str):
        """Handle enrichment error."""
        self.enrich_button.setEnabled(True)
        self.enrich_progress_bar.setVisible(False)
        self.enrich_progress_label.setVisible(False)
        self.log(f"Enrichment error: {error}")
        self.statusBar().showMessage("Enrichment failed")
        QMessageBox.critical(self, "Error", f"Enrichment failed:\n{error}")

    def show_video_context_menu(self, position):
        """Show context menu for video table."""
        if not self.current_playlist:
            return

        # Get the clicked row
        item = self.videos_table.itemAt(position)
        if not item:
            return

        row = item.row()
        video_id = self.videos_table.item(row, 0).data(Qt.UserRole)

        if not video_id:
            return

        # Create context menu
        menu = QMenu(self)

        # Download options
        download_video_action = menu.addAction("Download This Video")
        download_audio_action = menu.addAction("Download This Audio")
        download_comments_action = menu.addAction("Download Comments for This Video")
        menu.addSeparator()

        # Metadata option
        enrich_action = menu.addAction("Get Detailed Metadata for This Video")

        # Show menu and handle action
        action = menu.exec_(self.videos_table.viewport().mapToGlobal(position))

        if action == download_video_action:
            self.download_single_video(video_id, audio_only=False)
        elif action == download_audio_action:
            self.download_single_video(video_id, audio_only=True)
        elif action == download_comments_action:
            self.download_single_video_comments(video_id)
        elif action == enrich_action:
            self.enrich_single_video(video_id)

    def download_single_video(self, video_id: str, audio_only: bool = False):
        """Download a single video."""
        if not self.current_playlist or video_id not in self.current_playlist.videos:
            return

        video = self.current_playlist.videos[video_id]

        # Get quality from UI
        quality = self.quality_combo.currentText()

        media_type = "audio" if audio_only else "video"
        self.statusBar().showMessage(f"Downloading {media_type}: {video.title[:50]}...")
        self.log(f"Downloading {media_type}: {video.title}")

        # Create and start download thread
        self.single_download_thread = SingleVideoDownloadThread(
            self.downloader, self.storage, self.current_playlist, video_id, quality, audio_only
        )
        self.single_download_thread.finished.connect(
            lambda success: self.on_single_download_finished(success, video.title, media_type)
        )
        self.single_download_thread.error.connect(self.on_single_download_error)
        self.single_download_thread.start()

    def on_single_download_finished(self, success: bool, video_title: str, media_type: str):
        """Handle successful single video download."""
        if success:
            self.log(f"{media_type.capitalize()} downloaded: {video_title}")
            self.statusBar().showMessage(f"{media_type.capitalize()} downloaded successfully")

            # Reload the playlist from storage to pick up updated paths
            if self.current_playlist:
                reloaded = self.storage.load_playlist(self.current_playlist.playlist_id)
                if reloaded:
                    self.current_playlist = reloaded

            # Refresh display to show updated download status
            self.display_playlist()

            QMessageBox.information(
                self,
                "Success",
                f"{media_type.capitalize()} downloaded successfully:\n{video_title}"
            )
        else:
            self.log(f"Failed to download {media_type}: {video_title}")
            self.statusBar().showMessage(f"Failed to download {media_type}")
            QMessageBox.warning(
                self,
                "Warning",
                f"Failed to download {media_type}:\n{video_title}"
            )

    def on_single_download_error(self, error: str):
        """Handle single video download error."""
        self.log(f"Download error: {error}")
        self.statusBar().showMessage("Download failed")
        QMessageBox.critical(self, "Error", f"Download failed:\n{error}")

    def download_single_video_comments(self, video_id: str):
        """Download comments for a single video."""
        if not self.current_playlist or video_id not in self.current_playlist.videos:
            return

        video = self.current_playlist.videos[video_id]

        self.statusBar().showMessage(f"Downloading comments for: {video.title[:50]}...")
        self.log(f"Downloading comments for video: {video.title}")

        # Download comments in background
        try:
            output_dir = self.downloader.get_playlist_download_dir(self.current_playlist)
            success = self.downloader.download_comments(video, output_dir)

            if success:
                # Save playlist to persist comments path
                self.storage.save_playlist(self.current_playlist, create_version=False)

                # Reload the playlist from storage to pick up updated paths
                reloaded = self.storage.load_playlist(self.current_playlist.playlist_id)
                if reloaded:
                    self.current_playlist = reloaded

                self.log(f"Comments downloaded: {video.title}")
                self.statusBar().showMessage("Comments downloaded successfully")

                # Refresh display to show updated download status
                self.display_playlist()

                QMessageBox.information(
                    self,
                    "Success",
                    f"Comments downloaded for:\n{video.title}\n\nSaved to: {video.comments_path}"
                )
            else:
                self.log(f"Failed to download comments: {video.title}")
                self.statusBar().showMessage("Failed to download comments")
                QMessageBox.warning(
                    self,
                    "Warning",
                    "Failed to download comments for this video."
                )

        except Exception as e:
            self.log(f"Error downloading comments: {str(e)}")
            self.statusBar().showMessage("Error downloading comments")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to download comments:\n{str(e)}"
            )

    def enrich_single_video(self, video_id: str):
        """Enrich metadata for a single video."""
        if not self.current_playlist or video_id not in self.current_playlist.videos:
            return

        video = self.current_playlist.videos[video_id]

        self.statusBar().showMessage(f"Fetching detailed metadata for: {video.title[:50]}...")
        self.log(f"Fetching detailed metadata for video: {video.title}")

        # Fetch detailed metadata in background
        try:
            detailed = self.fetcher.fetch_video_metadata(video_id)

            if detailed:
                # Preserve existing data
                detailed.download_status = video.download_status
                detailed.video_path = video.video_path
                detailed.audio_path = video.audio_path
                detailed.comments_path = video.comments_path
                detailed.first_seen = video.first_seen
                detailed.status_history = video.status_history
                detailed.playlist_index = video.playlist_index

                # Update in current playlist
                self.current_playlist.videos[video_id] = detailed

                # Save playlist
                self.storage.save_playlist(self.current_playlist, create_version=False)

                self.log(f"Video metadata enriched: {detailed.title}")
                self.statusBar().showMessage("Video metadata enriched successfully")

                # Refresh display
                self.display_playlist()

                QMessageBox.information(
                    self,
                    "Success",
                    f"Detailed metadata fetched for:\n{detailed.title}"
                )
            else:
                self.log(f"Failed to fetch metadata for video: {video_id}")
                self.statusBar().showMessage("Failed to fetch video metadata")
                QMessageBox.warning(
                    self,
                    "Warning",
                    "Failed to fetch detailed metadata for this video."
                )

        except Exception as e:
            self.log(f"Error fetching video metadata: {str(e)}")
            self.statusBar().showMessage("Error fetching video metadata")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to fetch video metadata:\n{str(e)}"
            )

    def set_cookies(self):
        """Set cookies file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Cookies File", "", "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                self.auth_manager.set_cookies_file(file_path)
                self.log("Cookies file set successfully")
                self.update_auth_status()
                QMessageBox.information(self, "Success", "Cookies file set successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to set cookies:\n{str(e)}")

    def setup_oauth(self):
        """Setup OAuth authentication."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Client Secrets JSON", "", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                self.auth_manager.setup_oauth(file_path)
                self.log("OAuth configured successfully")
                self.update_auth_status()
                QMessageBox.information(self, "Success", "OAuth configured successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to setup OAuth:\n{str(e)}")

    def update_auth_status(self):
        """Update authentication status labels."""
        status = self.auth_manager.get_auth_status()

        if status['cookies']:
            self.cookies_path_label.setText("✓ Configured")
            self.cookies_path_label.setStyleSheet("color: green;")
        else:
            self.cookies_path_label.setText("✗ Not set")
            self.cookies_path_label.setStyleSheet("color: red;")

        if status['oauth']:
            self.oauth_status_label.setText("✓ Configured")
            self.oauth_status_label.setStyleSheet("color: green;")
        else:
            self.oauth_status_label.setText("✗ Not configured")
            self.oauth_status_label.setStyleSheet("color: red;")

    def log(self, message: str):
        """Add a message to the log."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")


def main():
    """Main entry point for GUI."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
