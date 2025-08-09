#!/usr/bin/env python3
"""
Setup script for Meme Coin Sniper Bot
Helps users configure the bot with basic settings
"""

import os
import sys
from pathlib import Path

def create_env_file():
    """Create .env file from template if it doesn't exist"""
    env_file = Path('.env')
    example_file = Path('.env.example')
    
    if env_file.exists():
        print("✅ .env file already exists")
        return
    
    if not example_file.exists():
        print("❌ .env.example file not found")
        return
    
    # Copy example to .env
    with open(example_file, 'r') as f:
        content = f.read()
    
    with open(env_file, 'w') as f:
        f.write(content)
    
    print("✅ Created .env file from template")
    print("⚠️  Please edit .env file with your actual configuration before running the bot")

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    
    print(f"✅ Python version {sys.version_info.major}.{sys.version_info.minor} is compatible")
    return True

def install_dependencies():
    """Install required dependencies"""
    try:
        import subprocess
        
        print("📦 Installing dependencies...")
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
            return True
        else:
            print("❌ Failed to install dependencies")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def create_logs_directory():
    """Create logs directory"""
    logs_dir = Path('logs')
    
    if not logs_dir.exists():
        logs_dir.mkdir()
        print("✅ Created logs directory")
    else:
        print("✅ Logs directory already exists")

def validate_configuration():
    """Basic validation of configuration"""
    try:
        from config import config
        
        print("\n🔍 Validating configuration...")
        
        # Check if basic configuration is present
        required_fields = ['ETHEREUM_RPC_URL', 'PRIVATE_KEY', 'WALLET_ADDRESS']
        missing_fields = []
        
        for field in required_fields:
            value = getattr(config, field, '')
            if not value or 'your_' in value.lower():
                missing_fields.append(field)
        
        if missing_fields:
            print("⚠️  Configuration incomplete. Please edit .env file and set:")
            for field in missing_fields:
                print(f"   - {field}")
            return False
        else:
            print("✅ Basic configuration looks good")
            return True
            
    except Exception as e:
        print(f"❌ Error validating configuration: {e}")
        return False

def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "="*60)
    print("🎯 SETUP COMPLETE!")
    print("="*60)
    print("\n📝 Next Steps:")
    print("1. Edit the .env file with your actual configuration:")
    print("   - Add your RPC URLs (Infura, Alchemy, etc.)")
    print("   - Add your wallet private key and address")
    print("   - Adjust trading parameters as needed")
    print("\n2. Fund your wallet with ETH for gas fees and trading")
    print("\n3. Test the bot with small amounts first")
    print("\n4. Run the bot:")
    print("   python sniper_bot.py")
    print("\n⚠️  IMPORTANT REMINDERS:")
    print("   - This is high-risk trading software")
    print("   - Start with small amounts")
    print("   - Never invest more than you can afford to lose")
    print("   - Monitor the bot closely")
    print("\n📚 For more information, read the README.md file")

def main():
    """Main setup function"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║              MEME COIN SNIPER BOT SETUP                     ║
║                   Version 1.0.0                            ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    print("🚀 Starting setup process...\n")
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Setup failed during dependency installation")
        sys.exit(1)
    
    # Create necessary directories
    create_logs_directory()
    
    # Create .env file
    create_env_file()
    
    # Validate configuration (will show warnings if incomplete)
    validate_configuration()
    
    # Print next steps
    print_next_steps()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Setup interrupted by user")
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        sys.exit(1)