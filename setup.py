"""Setup script for YouTube Playlist Downloader."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="ytpl-downloader",
    version="1.0.0",
    author="Your Name",
    description="A comprehensive YouTube playlist downloader with CLI and GUI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ytpl-downloader",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Video",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "yt-dlp>=2024.10.7",
        "PySide6>=6.6.0",
        "click>=8.1.7",
        "requests>=2.31.0",
        "google-auth-oauthlib>=1.2.0",
        "google-auth>=2.25.0",
        "tabulate>=0.9.0",
    ],
    entry_points={
        "console_scripts": [
            "ytpl-cli=ytpl_downloader.cli.main:main",
            "ytpl-gui=ytpl_downloader.gui.main:main",
        ],
    },
)
