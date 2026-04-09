#!/usr/bin/env python3
"""
Quick setup script for the CareerBuilder system.
Helps you get started quickly by checking dependencies and configuration.
"""

import sys
import subprocess
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✓ Python version: {sys.version_info.major}.{sys.version_info.minor}")
    return True


def install_dependencies():
    """Install required packages."""
    print("\nInstalling dependencies...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"
        ])
        print("✓ Dependencies installed")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False


def check_env_file():
    """Check if .env file exists."""
    env_file = Path(".env")
    if env_file.exists():
        print("✓ .env file found")
        return True
    else:
        print("⚠ .env file not found")
        print("  You can:")
        print("  1. Create .env from .env.example and add your API key")
        print("  2. Use Ollama (no API key needed)")
        return False


def check_ollama():
    """Check if Ollama is available."""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print("✓ Ollama is running")
            models = response.json().get("models", [])
            if models:
                print(f"  Available models: {', '.join([m['name'] for m in models[:3]])}")
            return True
    except:
        pass
    
    print("⚠ Ollama not detected")
    print("  Install from: https://ollama.ai")
    return False


def main():
    """Run setup checks."""
    print("=" * 60)
    print("  CareerBuilder - Setup Check")
    print("=" * 60)
    print()
    
    checks = []
    
    # Python version
    checks.append(check_python_version())
    
    # Dependencies
    checks.append(install_dependencies())
    
    # Configuration
    print("\nChecking LLM backend configuration...")
    env_ok = check_env_file()
    ollama_ok = check_ollama()
    
    if not env_ok and not ollama_ok:
        print("\n⚠ WARNING: No LLM backend configured!")
        print("  You need either:")
        print("  - An API key in .env file (Anthropic or OpenAI)")
        print("  - Ollama running locally")
        checks.append(False)
    else:
        checks.append(True)
    
    print("\n" + "=" * 60)
    if all(checks):
        print("✓ Setup complete! You're ready to run:")
        print("\n  python main.py\n")
    else:
        print("⚠ Setup incomplete. Please fix the issues above.")
    print("=" * 60)


if __name__ == "__main__":
    main()
