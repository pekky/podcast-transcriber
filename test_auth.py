#!/usr/bin/env python3
"""
Test pyannote authentication
"""

import os
from pathlib import Path

def main():
    print("🔐 Testing pyannote.audio authentication...")
    
    # Load token
    env_file = Path('.env')
    token = None
    
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('HF_TOKEN='):
                    token = line.split('=', 1)[1].strip()
                    print(f"✅ Token found: {token[:10]}...")
                    break
    
    if not token:
        print("❌ No token found in .env file")
        return False
    
    # Set environment variable
    os.environ['HF_TOKEN'] = token
    
    try:
        # Test Hugging Face API access
        from huggingface_hub import HfApi
        api = HfApi()
        user_info = api.whoami()
        print(f"✅ Hugging Face authentication successful")
        print(f"   Logged in as: {user_info.get('name', 'Unknown')}")
        
        # Test model access (just check if we can access the model info)
        print("🔍 Testing model access...")
        model_info = api.model_info("pyannote/speaker-diarization-3.1", token=token)
        print(f"✅ Model access successful: {model_info.modelId}")
        
        print("\n🎉 Authentication setup is complete!")
        print("💡 You can now run: python audio_transcriber.py <audio_file>")
        print("   High-precision speaker diarization will be used.")
        
        return True
        
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        
        if "gated" in str(e).lower():
            print("💡 Please visit https://hf.co/pyannote/speaker-diarization-3.1")
            print("   and accept the user conditions.")
        elif "token" in str(e).lower():
            print("💡 Please check your token is valid.")
        
        return False

if __name__ == "__main__":
    main()