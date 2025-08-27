"""Tests for the modular structure of the application."""
import pytest
from fastapi import APIRouter
import os


def test_api_router_exists():
    """Test that the API router is properly created."""
    try:
        from logic.api import router
        assert isinstance(router, APIRouter)
    except ImportError:
        pytest.fail("Failed to import API router")


def test_main_app_exists():
    """Test that the main app is properly created."""
    try:
        from main import app
        assert app is not None
    except ImportError:
        pytest.fail("Failed to import main app")


def test_file_structure():
    """Test that required files exist."""
    # Check main.py in root directory
    assert os.path.exists('main.py'), "Required file main.py does not exist"
    
    # Check files in logic directory
    required_files = ['logic/api.py', 'logic/service.py']
    for file in required_files:
        assert os.path.exists(file), f"Required file {file} does not exist"