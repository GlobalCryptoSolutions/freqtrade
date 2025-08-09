#!/bin/bash

# Hyperliquid Market Making Bot Setup Script
# This script sets up the environment and dependencies for the bot

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    printf "${1}${2}${NC}\n"
}

print_header() {
    echo
    print_color $BLUE "================================"
    print_color $BLUE "$1"
    print_color $BLUE "================================"
}

print_success() {
    print_color $GREEN "✓ $1"
}

print_warning() {
    print_color $YELLOW "⚠ $1"
}

print_error() {
    print_color $RED "✗ $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root for security reasons"
   exit 1
fi

print_header "Hyperliquid Market Making Bot Setup"
print_color $YELLOW "This script will set up the Hyperliquid market making bot environment"
echo

# Check Python version
print_header "Checking Python Installation"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_success "Python $PYTHON_VERSION found"
    
    # Check if version is 3.10 or higher
    if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        print_success "Python version is compatible"
    else
        print_error "Python 3.10 or higher is required, found $PYTHON_VERSION"
        exit 1
    fi
else
    print_error "Python 3 not found. Please install Python 3.10 or higher"
    exit 1
fi

# Check if we're in a Freqtrade installation
print_header "Checking Freqtrade Installation"
if [ -f "freqtrade/main.py" ] || [ -f "main.py" ]; then
    print_success "Freqtrade installation detected"
else
    print_warning "Freqtrade installation not detected in current directory"
    print_color $YELLOW "Please ensure you're running this script in your Freqtrade installation directory"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create necessary directories
print_header "Creating Directory Structure"
directories=(
    "user_data"
    "user_data/strategies"
    "user_data/data"
    "logs"
    "reports"
)

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        print_success "Created directory: $dir"
    else
        print_success "Directory exists: $dir"
    fi
done

# Check and install Python dependencies
print_header "Checking Python Dependencies"

# List of required packages
required_packages=(
    "freqtrade"
    "pandas>=2.2.0"
    "numpy"
    "talib-binary"
    "ccxt>=4.3.24"
    "sqlalchemy>=2.0.6"
)

missing_packages=()

for package in "${required_packages[@]}"; do
    package_name=$(echo "$package" | cut -d'>' -f1 | cut -d'=' -f1)
    if python3 -c "import $package_name" 2>/dev/null; then
        print_success "$package_name is installed"
    else
        print_warning "$package_name is missing"
        missing_packages+=("$package")
    fi
done

# Install missing packages
if [ ${#missing_packages[@]} -gt 0 ]; then
    print_color $YELLOW "Some packages are missing. Install them now? (y/N): "
    read -p "" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        for package in "${missing_packages[@]}"; do
            print_color $BLUE "Installing $package..."
            pip3 install "$package" --user
        done
    else
        print_warning "Skipping package installation. You may need to install them manually:"
        for package in "${missing_packages[@]}"; do
            echo "  pip install $package"
        done
    fi
fi

# Check TA-Lib installation
print_header "Checking TA-Lib Installation"
if python3 -c "import talib" 2>/dev/null; then
    print_success "TA-Lib is properly installed"
else
    print_warning "TA-Lib not found. Attempting to install..."
    
    # Detect OS and install TA-Lib
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        print_color $BLUE "Detected Linux system"
        if command -v apt-get &> /dev/null; then
            print_color $BLUE "Installing TA-Lib dependencies via apt-get..."
            sudo apt-get update
            sudo apt-get install -y build-essential wget
            
            # Download and compile TA-Lib
            cd /tmp
            wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
            tar -xzf ta-lib-0.4.0-src.tar.gz
            cd ta-lib/
            ./configure --prefix=/usr
            make
            sudo make install
            cd - > /dev/null
            
            pip3 install TA-Lib --user
        else
            print_error "apt-get not found. Please install TA-Lib manually"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        print_color $BLUE "Detected macOS system"
        if command -v brew &> /dev/null; then
            print_color $BLUE "Installing TA-Lib via Homebrew..."
            brew install ta-lib
            pip3 install TA-Lib --user
        else
            print_error "Homebrew not found. Please install TA-Lib manually"
        fi
    else
        print_error "Unsupported OS. Please install TA-Lib manually"
    fi
fi

# Setup configuration template
print_header "Setting up Configuration"

CONFIG_FILE="config_hyperliquid_market_maker.json"
if [ -f "$CONFIG_FILE" ]; then
    print_success "Configuration file already exists: $CONFIG_FILE"
else
    print_color $BLUE "Configuration file will be created when you run the setup"
    print_success "Configuration template ready"
fi

# Setup strategy files
print_header "Checking Strategy Files"

strategy_files=(
    "user_data/strategies/HyperliquidMarketMaker.py"
    "user_data/strategies/hyperliquid_risk_manager.py"
    "user_data/strategies/hyperliquid_monitor.py"
)

for file in "${strategy_files[@]}"; do
    if [ -f "$file" ]; then
        print_success "Strategy file exists: $file"
    else
        print_warning "Strategy file missing: $file"
    fi
done

# Make launcher executable
print_header "Setting up Launcher"
LAUNCHER="run_hyperliquid_market_maker.py"
if [ -f "$LAUNCHER" ]; then
    chmod +x "$LAUNCHER"
    print_success "Launcher is ready: $LAUNCHER"
else
    print_warning "Launcher not found: $LAUNCHER"
fi

# Setup systemd service (optional)
print_header "System Service Setup (Optional)"
print_color $YELLOW "Would you like to create a systemd service for the bot? (y/N): "
read -p "" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    SERVICE_FILE="/etc/systemd/system/hyperliquid-mm.service"
    WORKING_DIR=$(pwd)
    USER=$(whoami)
    
    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Hyperliquid Market Making Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$WORKING_DIR
ExecStart=/usr/bin/python3 $WORKING_DIR/run_hyperliquid_market_maker.py trade
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    print_success "Systemd service created: $SERVICE_FILE"
    print_color $BLUE "To enable and start the service:"
    print_color $BLUE "  sudo systemctl enable hyperliquid-mm"
    print_color $BLUE "  sudo systemctl start hyperliquid-mm"
    print_color $BLUE "To view logs:"
    print_color $BLUE "  sudo journalctl -u hyperliquid-mm -f"
fi

# Final setup summary
print_header "Setup Complete!"
echo
print_success "Hyperliquid Market Making Bot setup is complete!"
echo
print_color $BLUE "Next steps:"
print_color $BLUE "1. Configure your Hyperliquid API credentials in $CONFIG_FILE"
print_color $BLUE "2. Update the walletAddress and privateKey in the configuration"
print_color $BLUE "3. Test with dry-run mode:"
print_color $BLUE "   python3 $LAUNCHER trade --dry-run"
print_color $BLUE "4. Download historical data for backtesting:"
print_color $BLUE "   python3 $LAUNCHER download --days 30"
print_color $BLUE "5. Run a backtest:"
print_color $BLUE "   python3 $LAUNCHER backtest"
echo
print_color $YELLOW "Important Security Notes:"
print_color $YELLOW "- Never commit your private keys to version control"
print_color $YELLOW "- Use API wallets, not your main wallet private key"
print_color $YELLOW "- Start with small amounts for testing"
print_color $YELLOW "- Always test in dry-run mode first"
echo
print_color $GREEN "Setup completed successfully! 🚀"
print_color $GREEN "Happy market making!"