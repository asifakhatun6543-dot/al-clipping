"""
Unit tests for Video URL Downloader Service
"""

import pytest
from pathlib import Path
from services.url_downloader import sanitize_filename, VideoURLDownloader


def test_sanitize_filename():
    assert sanitize_filename("Normal Title") == "Normal_Title"
    assert sanitize_filename("Invalid: / ? < > \\ | * Name") == "Invalid_Name"
    long_name = "a" * 150
    assert len(sanitize_filename(long_name)) <= 80


def test_extract_url_metadata():
    downloader = VideoURLDownloader()
    # Test with standard public YouTube URL
    info = downloader.extract_info("https://youtu.be/4gWOqYhxiko")
    assert info is not None
    assert "10 Days" in info["title"] or "shorts" in info["title"].lower()
    assert info["duration"] > 0
    assert info["thumbnail"] is not None
