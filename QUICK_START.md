# Quick Start Guide - Hyperliquid Market Making Bot

Get your Hyperliquid market making bot up and running in minutes!

## 🚀 Quick Setup (5 minutes)

### 1. Run the Setup Script
```bash
./setup_hyperliquid_mm.sh
```
This will automatically:
- Check Python dependencies
- Install missing packages
- Create necessary directories
- Set up the environment

### 2. Configure Your API Keys
Edit `config_hyperliquid_market_maker.json`:

```json
{
  "exchange": {
    "name": "hyperliquid",
    "walletAddress": "0xYourMainWalletAddress",
    "privateKey": "0xYourAPIWalletPrivateKey"
  }
}
```

**Get your API keys:**
1. Visit [Hyperliquid API Generator](https://app.hyperliquid.xyz/API)
2. Create an API wallet
3. Copy the private key and your main wallet address

### 3. Test in Dry-Run Mode
```bash
python run_hyperliquid_market_maker.py trade --dry-run
```

### 4. Start Live Trading (when ready)
```bash
python run_hyperliquid_market_maker.py trade
```

## 📊 Quick Commands

```bash
# Check bot status
python run_hyperliquid_market_maker.py status

# Download data for backtesting
python run_hyperliquid_market_maker.py download --days 30

# Run a backtest
python run_hyperliquid_market_maker.py backtest --timerange 20240101-20240201

# View logs
tail -f logs/hyperliquid_mm_$(date +%Y%m%d).log
```

## ⚙️ Key Configuration Options

### Trading Pairs
```json
"pair_whitelist": [
  "BTC/USDC:USDC",
  "ETH/USDC:USDC"
]
```

### Market Making Side
- **Buy-side MM**: Places bids below market price
- **Sell-side MM**: Places asks above market price

Change in strategy parameters:
```python
buy_side_preference = True  # True for buy-side, False for sell-side
```

### Risk Settings
```json
"max_open_trades": 1,        # Limit concurrent pairs
"stake_amount": "unlimited", # Use available balance
"stoploss": -0.02           # 2% stop loss
```

## 🛡️ Safety First

1. **Always start with dry-run mode**
2. **Use small amounts initially**
3. **Test with API wallets, not main wallet**
4. **Monitor closely during initial runs**

## 📈 Default Strategy Settings

- **Timeframe**: 1-minute candles for fast execution
- **Grid Levels**: 4 levels for position scaling
- **Base Spread**: 0.1% spread from market price
- **Risk Management**: 2% stop loss, 80% max exposure

## 🔧 Customization Quick Tips

### Adjust Spreads
```python
base_spread_pct = 0.2  # Increase for wider spreads
```

### Change Grid Levels
```python
grid_levels = 6  # More levels for more aggressive scaling
```

### Modify Risk Limits
```python
max_position_size_pct = 0.3  # 30% max per position
```

## 🐛 Common Issues & Fixes

### "Connection Error"
- Check internet connection
- Verify API keys are correct
- Ensure Hyperliquid API is accessible

### "Insufficient Balance"
- Check USDC balance on Hyperliquid
- Reduce stake amount in config
- Verify wallet has trading balance

### "Strategy Not Found"
- Ensure files are in `user_data/strategies/`
- Check file permissions
- Verify Python path is correct

## 📞 Need Help?

1. Check the full [README](HYPERLIQUID_MARKET_MAKER_README.md)
2. Review log files in `logs/` directory
3. Test in dry-run mode first
4. Start with small amounts

## ⚠️ Important Reminders

- **This is experimental software**
- **Market making involves inventory risk**
- **Always start small and test thoroughly**
- **Never risk more than you can afford to lose**

---

**Happy Trading! 🚀**

Remember: The best traders are those who manage risk well!