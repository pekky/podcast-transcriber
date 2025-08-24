#!/usr/bin/env python3
"""
Setup Authentication for pyannote.audio

This script helps you configure Hugging Face authentication for pyannote models.
"""

import os
import sys
from pathlib import Path
import getpass

def setup_huggingface_token():
    """Setup Hugging Face authentication token."""
    print("🔐 Setting up Hugging Face Authentication")
    print("=" * 50)
    
    print("\n📋 Steps to get your token:")
    print("1. Visit: https://hf.co/settings/tokens")
    print("2. Create a new token with 'Read' permissions")
    print("3. Accept terms at: https://hf.co/pyannote/speaker-diarization-3.1")
    print("4. Accept terms at: https://hf.co/pyannote/segmentation-3.0")
    
    token = getpass.getpass("\n🔑 Enter your Hugging Face token: ").strip()
    
    if not token:
        print("❌ No token provided. Exiting.")
        return False
    
    # Save to environment variable file
    env_file = Path(".env")
    
    # Read existing content
    env_content = ""
    if env_file.exists():
        with open(env_file, 'r') as f:
            lines = f.readlines()
            # Remove existing HF_TOKEN lines
            lines = [line for line in lines if not line.startswith('HF_TOKEN=')]
            env_content = ''.join(lines)
    
    # Add new token
    env_content += f"HF_TOKEN={token}\n"
    
    # Write back
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"✅ Token saved to {env_file}")
    
    # Also try to save to ~/.huggingface/token
    hf_dir = Path.home() / ".huggingface"
    hf_dir.mkdir(exist_ok=True)
    hf_token_file = hf_dir / "token"
    
    try:
        with open(hf_token_file, 'w') as f:
            f.write(token)
        print(f"✅ Token also saved to {hf_token_file}")
    except Exception as e:
        print(f"⚠️  Could not save to {hf_token_file}: {e}")
    
    print("\n🎉 Authentication setup complete!")
    print("💡 You can now run: python audio_transcriber.py <audio_file>")
    
    return True

def test_authentication():
    """Test if authentication is working."""
    print("\n🧪 Testing authentication...")
    
    try:
        from huggingface_hub import HfApi
        
        # Load token from .env if it exists
        env_file = Path(".env")
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('HF_TOKEN='):
                        token = line.split('=', 1)[1].strip()
                        os.environ['HF_TOKEN'] = token
                        break
        
        api = HfApi()
        user_info = api.whoami()
        
        print(f"✅ Authentication successful!")
        print(f"   Logged in as: {user_info.get('name', 'Unknown')}")
        return True
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print("💡 Make sure you have a valid token and accepted the model terms.")
        return False

def main():
    print("🎤 pyannote.audio Authentication Setup")
    print("=" * 40)
    
    choice = input("\nWhat would you like to do?\n"
                  "1. Setup new token\n"
                  "2. Test existing authentication\n"
                  "Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        success = setup_huggingface_token()
        if success:
            test_authentication()
    elif choice == "2":
        test_authentication()
    else:
        print("Invalid choice. Exiting.")

if __name__ == "__main__":
    main()