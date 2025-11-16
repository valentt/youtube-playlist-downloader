"""Setup script for yt-transcript."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="yt-transcript",
    version="0.1.0",
    author="YouTube Transcript Tool",
    description="Download YouTube video transcripts/captions in multiple formats",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/valentt/yt-transcript",
    packages=find_packages(),
    install_requires=[
        "youtube-transcript-api>=0.6.0",
        "click>=8.1.7",
    ],
    entry_points={
        "console_scripts": [
            "yt-transcript=yt_transcript.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Video",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    keywords="youtube transcript subtitles captions download cli",
)
