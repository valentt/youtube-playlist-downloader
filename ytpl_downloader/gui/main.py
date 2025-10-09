"""Graphical user interface for YouTube playlist downloader."""

import sys
from pathlib import Path
from typing import Optional, List
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QTableWidget, QTableWidgetItem,
    QComboBox, QSpinBox, QCheckBox, QTabWidget, QTextEdit,
    QFileDialog, QMessageBox, QProgressBar, QHeaderView, QGroupBox
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

    def __init__(self, fetcher: PlaylistFetcher, url: str):
        super().__init__()
        self.fetcher = fetcher
        self.url = url

    def run(self):
        try:
            playlist = self.fetcher.fetch_playlist(self.url, quiet=False)
            self.finished.emit(playlist)
        except Exception as e:
            self.error.emit(str(e))


class DownloadThread(QThread):
    """Background thread for downloading playlists."""
    finished = Signal(dict)  # results
    error = Signal(str)
    progress = Signal(str)  # status message

    def __init__(self, downloader: DownloadManager, playlist: PlaylistMetadata,
                 quality: str, audio_only: bool, metadata_only: bool, workers: int):
        super().__init__()
        self.downloader = downloader
        self.playlist = playlist
        self.quality = quality
        self.audio_only = audio_only
        self.metadata_only = metadata_only
        self.workers = workers

    def run(self):
        try:
            results = self.downloader.download_playlist(
                self.playlist,
                quality=self.quality,
                audio_only=self.audio_only,
                download_metadata_only=self.metadata_only,
                max_workers=self.workers
            )
            self.finished.emit(results)
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
        layout.addWidget(fetch_group)

        # Playlists list
        playlists_group = QGroupBox("Stored Playlists")
        playlists_layout = QVBoxLayout(playlists_group)

        self.playlists_table = QTableWidget()
        self.playlists_table.setColumnCount(4)
        self.playlists_table.setHorizontalHeaderLabels(["Playlist ID", "Title", "Videos", "Last Updated"])
        self.playlists_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.playlists_table.setSelectionBehavior(QTableWidget.SelectRows)
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
        self.videos_table.setColumnCount(6)
        self.videos_table.setHorizontalHeaderLabels(["#", "Video ID", "Title", "Channel", "Status", "Downloaded"])
        self.videos_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.videos_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.videos_table)

        # Download controls
        download_group = QGroupBox("Download Options")
        download_layout = QVBoxLayout(download_group)

        # Quality and options
        options_layout = QHBoxLayout()

        options_layout.addWidget(QLabel("Quality:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["1080p", "720p", "best"])
        options_layout.addWidget(self.quality_combo)

        self.audio_only_checkbox = QCheckBox("Audio Only")
        options_layout.addWidget(self.audio_only_checkbox)

        self.metadata_only_checkbox = QCheckBox("Metadata Only")
        options_layout.addWidget(self.metadata_only_checkbox)

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

        self.fetch_button.setEnabled(False)
        self.statusBar().showMessage("Fetching playlist...")
        self.log("Fetching playlist: " + url)

        # Create and start fetch thread
        self.fetch_thread = FetchThread(self.fetcher, url)
        self.fetch_thread.finished.connect(self.on_fetch_finished)
        self.fetch_thread.error.connect(self.on_fetch_error)
        self.fetch_thread.start()

    def on_fetch_finished(self, playlist: PlaylistMetadata):
        """Handle successful playlist fetch."""
        self.fetch_button.setEnabled(True)

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
        self.log(f"Error fetching playlist: {error}")
        self.statusBar().showMessage("Error fetching playlist")
        QMessageBox.critical(self, "Error", f"Failed to fetch playlist:\n{error}")

    def refresh_playlists_list(self):
        """Refresh the playlists list."""
        playlists = self.storage.list_playlists()
        self.playlists_table.setRowCount(len(playlists))

        for row, playlist in enumerate(playlists):
            self.playlists_table.setItem(row, 0, QTableWidgetItem(playlist['playlist_id']))
            self.playlists_table.setItem(row, 1, QTableWidgetItem(playlist['title']))
            self.playlists_table.setItem(row, 2, QTableWidgetItem(str(playlist['video_count'])))
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
        playlist_id = self.playlists_table.item(row, 0).text()

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
        playlist_id = self.playlists_table.item(row, 0).text()

        playlist = self.storage.load_playlist(playlist_id)
        if not playlist:
            QMessageBox.critical(self, "Error", "Failed to load playlist")
            return

        # Use the webpage_url to re-fetch
        self.url_input.setText(playlist.webpage_url)
        self.fetch_playlist()

    def display_playlist(self):
        """Display the current playlist in the videos tab."""
        if not self.current_playlist:
            return

        self.playlist_info_label.setText(
            f"Playlist: {self.current_playlist.title} ({len(self.current_playlist.videos)} videos)"
        )
        self.download_button.setEnabled(True)

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
            self.videos_table.setItem(row, 0, QTableWidgetItem(str(video.playlist_index)))
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

            downloaded_item = QTableWidgetItem("✓" if video.download_status == DownloadStatus.COMPLETED else "✗")
            self.videos_table.setItem(row, 5, downloaded_item)

    def download_playlist(self):
        """Download the current playlist."""
        if not self.current_playlist:
            return

        quality = self.quality_combo.currentText()
        audio_only = self.audio_only_checkbox.isChecked()
        metadata_only = self.metadata_only_checkbox.isChecked()
        workers = self.workers_spinbox.value()

        self.download_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(0)  # Indeterminate
        self.statusBar().showMessage("Downloading...")
        self.log(f"Starting download: {self.current_playlist.title}")

        # Create and start download thread
        self.download_thread = DownloadThread(
            self.downloader, self.current_playlist,
            quality, audio_only, metadata_only, workers
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
            self.log(f"Download complete: {successful}/{len(results)} successful")
            self.statusBar().showMessage("Download complete")
            QMessageBox.information(self, "Success", f"Download complete!\n{successful}/{len(results)} videos successful")
        else:
            self.log("Metadata saved (no downloads)")
            self.statusBar().showMessage("Metadata saved")

        # Refresh display
        self.display_playlist()

    def on_download_error(self, error: str):
        """Handle download error."""
        self.download_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.log(f"Download error: {error}")
        self.statusBar().showMessage("Download failed")
        QMessageBox.critical(self, "Error", f"Download failed:\n{error}")

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
