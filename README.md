# Meme Coin Sniper Bot 🤖

A sophisticated, automated trading bot for detecting and trading newly launched meme coins on decentralized exchanges (DEXs) like Uniswap and PancakeSwap.

## ⚠️ **DISCLAIMER**

**This software is provided for educational purposes only. Trading cryptocurrencies involves substantial risk and may result in significant financial losses. The authors are not responsible for any financial losses incurred through the use of this software. Use at your own risk and never invest more than you can afford to lose.**

## 🚀 Features

### Core Functionality
- **Multi-Chain Support**: Monitor Ethereum, BSC, and other EVM-compatible chains
- **Real-Time Monitoring**: Detect new token pairs as they're created on DEXs
- **Advanced Analysis**: Comprehensive token safety analysis including:
  - Honeypot detection
  - Liquidity analysis
  - Contract verification checks
  - Ownership analysis
  - Risk scoring
- **Automated Trading**: Execute trades automatically based on configurable criteria
- **Gas Optimization**: Smart gas pricing for faster transaction execution

### Risk Management
- **Stop-Loss Protection**: Automatic stop-loss execution to limit losses
- **Take-Profit Targets**: Automatic profit-taking at configured levels
- **Position Monitoring**: Real-time tracking of all positions
- **Daily Loss Limits**: Built-in daily loss protection
- **Portfolio Risk Controls**: Maximum exposure and position size limits

### Monitoring & Notifications
- **Real-Time Logging**: Comprehensive logging with color-coded output
- **Telegram Integration**: Optional Telegram notifications for trades and alerts
- **Performance Tracking**: Detailed statistics and performance metrics
- **Risk Event Monitoring**: Track all risk management events

## 📋 Requirements

- Python 3.8 or higher
- Valid RPC endpoints (Infura, Alchemy, etc.)
- Wallet with private key for trading
- ETH/BNB for gas fees and trading capital

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd meme-coin-sniper-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

## ⚙️ Configuration

Edit the `.env` file with your settings:

### Blockchain Configuration
```env
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_INFURA_KEY
BSC_RPC_URL=https://bsc-dataseed.binance.org/
```

### Wallet Configuration
```env
PRIVATE_KEY=your_private_key_here
WALLET_ADDRESS=your_wallet_address_here
```

### Trading Parameters
```env
DEFAULT_BUY_AMOUNT_ETH=0.01          # Amount to spend per trade
DEFAULT_SLIPPAGE=5                   # Slippage tolerance (%)
PROFIT_TARGET_PERCENT=50             # Take profit at 50%
STOP_LOSS_PERCENT=30                 # Stop loss at -30%
```

### Risk Management
```env
MIN_LIQUIDITY_ETH=1.0               # Minimum liquidity required
MAX_BUY_TAX=10                      # Maximum buy tax (%)
MAX_SELL_TAX=10                     # Maximum sell tax (%)
ENABLE_HONEYPOT_CHECK=true          # Enable honeypot detection
```

### Optional: Telegram Notifications
```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## 🚀 Usage

### Basic Usage
```bash
python sniper_bot.py
```

### Running with Specific Chains
Edit the `main()` function in `sniper_bot.py`:
```python
chains = ['ethereum', 'bsc']  # Add chains as needed
bot = MemeCoinSniperBot(chains)
```

### Testing Individual Components
```bash
# Test DEX monitoring
python dex_monitor.py

# Test token analysis
python token_analyzer.py

# Test trading functionality
python trader.py
```

## 📊 How It Works

1. **Detection Phase**
   - Monitor blockchain for new pair creation events
   - Detect PairCreated events from DEX factory contracts
   - Extract token and pair information

2. **Analysis Phase**
   - Fetch token metadata (name, symbol, decimals, supply)
   - Analyze liquidity depth and market cap
   - Perform honeypot and safety checks
   - Calculate risk score based on multiple factors

3. **Decision Phase**
   - Apply risk management filters
   - Check if token passes safety criteria
   - Verify trading limits and exposure

4. **Execution Phase**
   - Execute buy orders with optimized gas
   - Set up stop-loss and take-profit orders
   - Monitor position continuously

5. **Management Phase**
   - Track price movements
   - Execute stop-loss/take-profit when triggered
   - Update trailing stops for profitable positions

## 🛡️ Safety Features

### Built-in Protections
- **Honeypot Detection**: Attempts to detect tokens that can't be sold
- **Liquidity Checks**: Ensures minimum liquidity before trading
- **Tax Analysis**: Checks for excessive buy/sell taxes
- **Ownership Analysis**: Analyzes token ownership concentration
- **Contract Verification**: Checks if contracts are verified

### Risk Controls
- **Daily Loss Limits**: Stops trading after daily loss threshold
- **Position Limits**: Maximum number of concurrent positions
- **Exposure Limits**: Maximum total capital at risk
- **Gas Price Caps**: Prevents excessive gas spending

## 📈 Performance Monitoring

The bot tracks and reports:
- Number of pairs detected
- Tokens analyzed
- Trades executed
- Success rate
- Profit/Loss tracking
- Best and worst trades
- Daily statistics

## 🔧 Customization

### Modifying Risk Parameters
Edit values in `config.py` or `.env` file:
- Adjust minimum liquidity requirements
- Change profit targets and stop-loss levels
- Modify risk scoring weights
- Update gas optimization parameters

### Adding New Chains
1. Add RPC URL to configuration
2. Add chain-specific contract addresses
3. Update the chains list in `main()`

### Custom Analysis Criteria
Modify the `TokenAnalyzer` class in `token_analyzer.py`:
- Add new safety checks
- Implement custom scoring algorithms
- Integrate external APIs for additional data

## 📝 File Structure

```
├── sniper_bot.py          # Main bot application
├── config.py              # Configuration management
├── logger.py              # Logging setup
├── dex_monitor.py         # DEX monitoring and event detection
├── token_analyzer.py      # Token analysis and safety checks
├── trader.py              # Trading execution and position management
├── risk_manager.py        # Risk management and position monitoring
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variables template
└── README.md             # This file
```

## 🐛 Troubleshooting

### Common Issues

1. **Configuration Errors**
   - Verify all required environment variables are set
   - Check that private key and wallet address match
   - Ensure RPC URLs are valid and accessible

2. **Network Issues**
   - Check internet connection
   - Verify RPC endpoint status
   - Increase timeout values if needed

3. **Trading Failures**
   - Ensure sufficient ETH/BNB for gas fees
   - Check if tokens have trading restrictions
   - Verify slippage tolerance is appropriate

4. **Performance Issues**
   - Use faster RPC endpoints
   - Reduce monitoring frequency
   - Optimize gas price settings

### Logs and Debugging
- Logs are saved to `logs/` directory when `LOG_TO_FILE=true`
- Set `LOG_LEVEL=DEBUG` for detailed debugging information
- Monitor console output for real-time status

## 📚 Advanced Usage

### Multiple Bot Instances
You can run multiple instances with different configurations:
```bash
# Instance 1: Ethereum only, conservative settings
python sniper_bot.py

# Instance 2: BSC only, aggressive settings  
# (modify config for different parameters)
python sniper_bot.py
```

### API Integration
The bot can be extended with external APIs:
- Price oracles for better market cap calculations
- Social sentiment analysis
- Contract audit APIs
- Additional honeypot detection services

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Final Warning

**Cryptocurrency trading is extremely risky and volatile. This bot is a tool that may help automate trading decisions, but it cannot guarantee profits and may result in significant losses. Always:**

- Start with small amounts
- Test thoroughly in a safe environment
- Monitor the bot's performance closely
- Never invest more than you can afford to lose
- Understand the risks of automated trading
- Be aware of the legal implications in your jurisdiction

**The developers of this software are not responsible for any financial losses incurred through its use.**
