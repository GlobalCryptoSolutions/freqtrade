# Hyperliquid One-Sided Market Making Bot

A sophisticated market making bot designed specifically for Hyperliquid exchange, implementing one-sided market making strategies with advanced risk management and monitoring capabilities.

## 🚀 Features

### Core Market Making
- **One-sided market making** with configurable buy/sell side preference
- **Grid-based order placement** with multiple price levels
- **Dynamic spread adjustment** based on market volatility
- **Position adjustment** for grid-like scaling into positions
- **Intelligent order placement** using custom entry/exit pricing

### Risk Management
- **Position size limits** with maximum exposure controls
- **Drawdown protection** with automatic shutdown triggers
- **Liquidity management** to maintain sufficient cash reserves
- **Volatility-based position sizing**
- **Consecutive loss protection**

### Monitoring & Analytics
- **Real-time performance tracking** with SQLite database storage
- **Market making specific metrics** (spread capture, fill rates, etc.)
- **Alert system** with configurable thresholds
- **Performance reporting** and data export
- **Live status monitoring**

### Technical Features
- **Built on Freqtrade** framework for reliability and extensive features
- **Hyperliquid native integration** with futures trading support
- **Custom price calculation** for optimal order placement
- **Comprehensive logging** and error handling
- **Backtesting support** for strategy validation

## 📋 Requirements

### System Requirements
- Python 3.10 or higher
- Linux/macOS (recommended) or Windows
- Minimum 4GB RAM
- Stable internet connection

### Python Dependencies
All dependencies are included in the Freqtrade installation:
- freqtrade>=2023.12
- ccxt>=4.3.24
- pandas>=2.2.0
- numpy<2.0
- TA-Lib
- SQLAlchemy>=2.0.6

## 🛠️ Installation & Setup

### 1. Clone and Setup Environment

```bash
# Navigate to your freqtrade installation directory
cd /path/to/freqtrade

# The bot files should be placed in the freqtrade workspace
# Files are already created in the workspace structure
```

### 2. Configure Hyperliquid API Access

1. **Create API Wallet on Hyperliquid:**
   - Visit [Hyperliquid API Generator](https://app.hyperliquid.xyz/API)
   - Generate a new API wallet
   - Save the private key securely
   - Note your main wallet address

2. **Fund Your Account:**
   - Deposit USDC to your Hyperliquid account
   - Bridge assets to Arbitrum if needed
   - Ensure sufficient balance for trading

### 3. Configure the Bot

Edit `config_hyperliquid_market_maker.json`:

```json
{
  "exchange": {
    "name": "hyperliquid",
    "walletAddress": "0xYourMainWalletAddress",
    "privateKey": "0xYourAPIWalletPrivateKey",
    // ... other settings
  },
  "pair_whitelist": [
    "BTC/USDC:USDC",
    "ETH/USDC:USDC"
  ],
  "stake_amount": "unlimited",  // Use all available balance
  "max_open_trades": 1,        // Limit concurrent pairs
  // ... other configuration
}
```

**⚠️ Security Notes:**
- Never commit your private keys to version control
- Use environment variables for sensitive data
- Use API wallets, not your main wallet private key
- Start with small amounts for testing

### 4. Install Dependencies

```bash
# Ensure all required Python packages are installed
pip install -r requirements.txt

# Install TA-Lib if not already installed
# On Ubuntu/Debian:
sudo apt-get install build-essential
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
pip install TA-Lib

# On macOS:
brew install ta-lib
pip install TA-Lib
```

## 🚀 Usage

### Running the Bot

```bash
# Make the launcher executable
chmod +x run_hyperliquid_market_maker.py

# Run in dry-run mode (recommended for testing)
python run_hyperliquid_market_maker.py trade --dry-run

# Run live trading (use with caution)
python run_hyperliquid_market_maker.py trade

# Run with increased verbosity
python run_hyperliquid_market_maker.py trade -vv
```

### Backtesting

```bash
# Download historical data (30 days)
python run_hyperliquid_market_maker.py download --days 30

# Run backtest for specific timerange
python run_hyperliquid_market_maker.py backtest --timerange 20240101-20240201

# Export backtest results
python run_hyperliquid_market_maker.py backtest --export trades,signals
```

### Monitoring

```bash
# Check bot status
python run_hyperliquid_market_maker.py status

# Monitor logs
tail -f logs/hyperliquid_mm_$(date +%Y%m%d).log

# View Freqtrade logs
tail -f logs/freqtrade_$(date +%Y%m%d).log
```

## ⚙️ Configuration

### Strategy Parameters

The market making strategy includes several configurable parameters:

```python
# Market making side preference
buy_side_preference = True  # True for buy-side MM, False for sell-side

# Grid configuration
grid_levels = 4            # Number of grid levels (2-8)
base_spread_pct = 0.1      # Base spread percentage (0.05-0.5%)
grid_spacing_pct = 0.1     # Grid spacing percentage (0.05-0.3%)

# Risk management
max_position_size_pct = 0.5    # Max position size (0.1-1.0)
volatility_adjustment = True   # Enable volatility-based adjustments

# Dynamic parameters
volatility_lookback = 20       # Volatility calculation period (10-50)
volatility_multiplier = 1.5    # Volatility adjustment factor (0.5-3.0)
```

### Risk Management Settings

Configure in the launcher script or strategy:

```python
risk_config = {
    'max_total_exposure': 0.8,      # 80% max capital exposure
    'max_single_position': 0.2,     # 20% max per position
    'max_drawdown_threshold': 0.1,  # 10% max drawdown before halt
    'min_liquidity_ratio': 0.3,     # 30% cash reserve requirement
    'max_consecutive_losses': 5     # Emergency halt after 5 losses
}
```

### Alert Thresholds

```python
alert_thresholds = {
    'max_drawdown': 0.05,      # 5% drawdown alert
    'min_liquidity': 0.2,      # 20% min liquidity alert
    'max_positions': 10        # Maximum position count alert
}
```

## 📊 Strategy Logic

### One-Sided Market Making

The bot implements a one-sided market making approach:

1. **Side Selection**: Choose to provide liquidity on either buy-side or sell-side
2. **Entry Conditions**: Enter positions when market conditions are favorable
3. **Price Placement**: Place orders with calculated spreads below (buy-side) or above (sell-side) market price
4. **Grid Scaling**: Add to positions at predetermined price levels
5. **Exit Management**: Close positions when profit targets are reached or market conditions change

### Market Quality Assessment

The strategy evaluates market conditions using:

- **Volume Analysis**: Minimum volume requirements and volume ratios
- **Volatility Metrics**: ATR and rolling volatility measurements
- **Trend Indicators**: ADX, RSI, and moving averages
- **Market Microstructure**: Bid-ask spreads and market depth
- **Support/Resistance**: Dynamic pivot levels

### Risk Controls

Multiple layers of risk management:

1. **Position Limits**: Maximum exposure per pair and total
2. **Volatility Adjustments**: Reduce position sizes during high volatility
3. **Emergency Stops**: Automatic shutdown on excessive drawdown
4. **Time Filters**: Avoid low-liquidity periods
5. **Market Quality Filters**: Skip trading during poor market conditions

## 📈 Monitoring & Analytics

### Real-Time Monitoring

The bot provides comprehensive monitoring through:

- **SQLite Database**: Persistent storage of all metrics and trades
- **Live Status**: Real-time performance and position information
- **Alert System**: Configurable alerts for risk events
- **Log Analysis**: Detailed logging for debugging and analysis

### Key Metrics Tracked

- **Spread Capture**: Average spread captured per trade
- **Fill Rates**: Percentage of orders successfully filled
- **Inventory Balance**: Current position imbalances
- **Market Impact**: Price impact of trades
- **Slippage**: Difference between expected and actual execution prices
- **Liquidity Provided**: Volume of liquidity added to the market

### Performance Reports

Generate detailed reports:

```python
# Export 7-day performance report
monitor.export_performance_report('reports/performance_7d.json', days=7)

# Get live dashboard data
dashboard_data = monitor.get_dashboard_data(current_trades, wallet_balance)
```

## 🔧 Customization

### Modifying Strategy Parameters

1. **Edit Strategy File**: Modify `user_data/strategies/HyperliquidMarketMaker.py`
2. **Adjust Parameters**: Change the parameter defaults or ranges
3. **Test Changes**: Run backtests to validate modifications
4. **Deploy**: Apply changes to live trading

### Adding Custom Indicators

```python
def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
    # Add your custom indicators here
    dataframe['custom_indicator'] = your_custom_calculation(dataframe)
    return dataframe
```

### Custom Risk Rules

Extend the risk manager:

```python
def custom_risk_check(self, current_trades, market_data):
    # Implement custom risk logic
    if your_condition:
        return False  # Prevent trading
    return True
```

## 🐛 Troubleshooting

### Common Issues

1. **Connection Errors**
   - Check internet connectivity
   - Verify Hyperliquid API status
   - Ensure correct wallet address and private key

2. **Order Failures**
   - Check account balance
   - Verify pair is available for trading
   - Review minimum order sizes

3. **Performance Issues**
   - Monitor system resources
   - Check log files for errors
   - Verify data feed stability

### Debug Mode

Run with debug logging:

```bash
python run_hyperliquid_market_maker.py trade --log-level DEBUG -vv
```

### Log Analysis

Important log files:
- `logs/hyperliquid_mm_YYYYMMDD.log`: Main bot logs
- `logs/freqtrade_YYYYMMDD.log`: Freqtrade system logs
- `user_data/hyperliquid_monitor.db`: Metrics database

## 📚 Additional Resources

### Hyperliquid Documentation
- [Hyperliquid Docs](https://hyperliquid.gitbook.io/hyperliquid-docs/)
- [API Documentation](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api)
- [Trading Guide](https://hyperliquid.gitbook.io/hyperliquid-docs/onboarding/how-to-start-trading)

### Freqtrade Resources
- [Freqtrade Documentation](https://www.freqtrade.io/)
- [Strategy Development](https://www.freqtrade.io/en/stable/strategy-customization/)
- [Configuration Guide](https://www.freqtrade.io/en/stable/configuration/)

## ⚠️ Risk Disclaimer

**IMPORTANT**: This software is for educational and informational purposes only. Trading cryptocurrencies involves substantial risk of loss and is not suitable for all investors. 

- **Start with small amounts** and dry-run mode
- **Never risk more than you can afford to lose**
- **Understand the risks** of algorithmic trading
- **Market making involves inventory risk** and potential losses
- **The authors assume no responsibility** for trading results

### Security Best Practices

1. **API Security**:
   - Use API wallets, not main wallet keys
   - Regularly rotate API keys
   - Monitor API access logs

2. **System Security**:
   - Keep software updated
   - Use secure, dedicated systems
   - Implement proper backup procedures

3. **Operational Security**:
   - Start with conservative settings
   - Monitor positions closely
   - Have emergency stop procedures

## 🤝 Support & Contributing

### Getting Help

1. **Check Documentation**: Review this README and Freqtrade docs
2. **Review Logs**: Check log files for error messages
3. **Test in Dry-Run**: Validate setup before live trading

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Test thoroughly
4. Submit a pull request

## 📄 License

This project is provided under the same license as Freqtrade (GPLv3). See the LICENSE file for details.

---

**Happy Market Making! 🚀📈**

Remember: Start small, test thoroughly, and never risk more than you can afford to lose.