#!/usr/bin/env python3
"""
Hyperliquid Market Making Bot Launcher
Main script to run the one-sided market making bot on Hyperliquid
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Add the workspace to the Python path
sys.path.insert(0, '/workspace')
sys.path.insert(0, '/workspace/user_data/strategies')

from freqtrade.main import main as freqtrade_main
from hyperliquid_risk_manager import create_risk_manager
from hyperliquid_monitor import create_monitor


def setup_logging(log_level: str = "INFO"):
    """Setup comprehensive logging for the market making bot"""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # File handler for all logs
    file_handler = logging.FileHandler(
        f"logs/hyperliquid_mm_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Console handler for important logs
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Specific loggers
    logging.getLogger("freqtrade").setLevel(logging.INFO)
    logging.getLogger("HyperliquidMarketMaker").setLevel(logging.DEBUG)
    logging.getLogger("hyperliquid_risk_manager").setLevel(logging.INFO)
    logging.getLogger("hyperliquid_monitor").setLevel(logging.INFO)
    
    logging.info("Logging initialized for Hyperliquid Market Making Bot")


def validate_configuration():
    """Validate the bot configuration before starting"""
    
    config_file = Path("config_hyperliquid_market_maker.json")
    
    if not config_file.exists():
        logging.error(f"Configuration file not found: {config_file}")
        sys.exit(1)
    
    # Check strategy file
    strategy_file = Path("user_data/strategies/HyperliquidMarketMaker.py")
    if not strategy_file.exists():
        logging.error(f"Strategy file not found: {strategy_file}")
        sys.exit(1)
    
    # Check data directory
    data_dir = Path("user_data/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    logging.info("Configuration validation completed")


def run_market_maker(args):
    """Run the Hyperliquid market making bot"""
    
    # Validate environment
    validate_configuration()
    
    # Setup logging
    setup_logging(args.log_level)
    
    logging.info("=" * 60)
    logging.info("STARTING HYPERLIQUID MARKET MAKING BOT")
    logging.info("=" * 60)
    
    # Build Freqtrade arguments
    freqtrade_args = [
        "trade",
        "--config", "config_hyperliquid_market_maker.json",
        "--strategy", "HyperliquidMarketMaker",
        "--logfile", f"logs/freqtrade_{datetime.now().strftime('%Y%m%d')}.log"
    ]
    
    if args.dry_run:
        freqtrade_args.append("--dry-run")
        logging.info("Running in DRY RUN mode")
    
    if args.verbosity:
        freqtrade_args.extend(["-v"] * args.verbosity)
    
    try:
        # Initialize risk manager and monitor (they will be used by the strategy)
        logging.info("Initializing risk management and monitoring systems...")
        
        # Create basic config for risk manager and monitor
        config = {
            'max_total_exposure': 0.8,
            'max_single_position': 0.2,
            'max_drawdown_threshold': 0.1,
            'min_liquidity_ratio': 0.3,
            'max_consecutive_losses': 5,
            'monitor_db_path': 'user_data/hyperliquid_monitor.db',
            'log_level': args.log_level
        }
        
        risk_manager = create_risk_manager(config)
        monitor = create_monitor(config)
        
        logging.info("Risk manager and monitor initialized successfully")
        
        # Start Freqtrade
        logging.info(f"Starting Freqtrade with args: {' '.join(freqtrade_args)}")
        
        # Modify sys.argv for Freqtrade
        original_argv = sys.argv.copy()
        sys.argv = ["freqtrade"] + freqtrade_args
        
        # Run Freqtrade
        freqtrade_main()
        
    except KeyboardInterrupt:
        logging.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logging.error(f"Bot crashed with error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Restore original argv
        sys.argv = original_argv
        logging.info("Hyperliquid Market Making Bot shutdown complete")


def run_backtest(args):
    """Run backtesting for the strategy"""
    
    validate_configuration()
    setup_logging(args.log_level)
    
    logging.info("Starting backtesting...")
    
    freqtrade_args = [
        "backtesting",
        "--config", "config_hyperliquid_market_maker.json",
        "--strategy", "HyperliquidMarketMaker",
        "--timeframe", "1m"
    ]
    
    if args.timerange:
        freqtrade_args.extend(["--timerange", args.timerange])
    
    if args.export:
        freqtrade_args.extend(["--export", args.export])
    
    try:
        original_argv = sys.argv.copy()
        sys.argv = ["freqtrade"] + freqtrade_args
        freqtrade_main()
    finally:
        sys.argv = original_argv


def download_data(args):
    """Download historical data for backtesting"""
    
    validate_configuration()
    setup_logging(args.log_level)
    
    logging.info("Downloading historical data...")
    
    freqtrade_args = [
        "download-data",
        "--config", "config_hyperliquid_market_maker.json",
        "--timeframes", "1m",
        "--days", str(args.days)
    ]
    
    if args.pairs:
        freqtrade_args.extend(["--pairs"] + args.pairs)
    
    try:
        original_argv = sys.argv.copy()
        sys.argv = ["freqtrade"] + freqtrade_args
        freqtrade_main()
    finally:
        sys.argv = original_argv


def show_status():
    """Show current bot status and statistics"""
    
    from hyperliquid_monitor import create_monitor
    
    config = {'monitor_db_path': 'user_data/hyperliquid_monitor.db'}
    monitor = create_monitor(config)
    
    try:
        stats = monitor.get_live_stats()
        
        print("\n" + "=" * 60)
        print("HYPERLIQUID MARKET MAKER STATUS")
        print("=" * 60)
        print(f"Timestamp: {stats['timestamp']}")
        print(f"Uptime: {stats['uptime_hours']:.2f} hours")
        
        if stats['recent_metrics']:
            metrics = stats['recent_metrics']
            print(f"\nRecent Performance (1 hour):")
            print(f"  Average Spread: {metrics.get('avg_spread', 0):.6f}")
            print(f"  Fill Rate: {metrics.get('avg_fill_rate', 0):.3f}")
            print(f"  Total Entries: {metrics.get('entries', 0)}")
        
        if stats['latest_performance']:
            perf = stats['latest_performance']
            print(f"\nLatest Performance:")
            print(f"  Total PnL: {perf.get('total_pnl', 0):.4f}")
            print(f"  Open Positions: {perf.get('open_positions', 0)}")
            print(f"  Max Drawdown: {perf.get('max_drawdown', 0):.3f}")
        
        if stats['pending_alerts']:
            print(f"\nPending Alerts:")
            for alert in stats['pending_alerts']:
                print(f"  {alert['severity']}: {alert['count']} alerts")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"Error retrieving status: {e}")


def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description="Hyperliquid One-Sided Market Making Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run live trading
  python run_hyperliquid_market_maker.py trade

  # Run in dry-run mode
  python run_hyperliquid_market_maker.py trade --dry-run

  # Download data for backtesting
  python run_hyperliquid_market_maker.py download --days 30

  # Run backtest
  python run_hyperliquid_market_maker.py backtest --timerange 20240101-20240201

  # Show current status
  python run_hyperliquid_market_maker.py status
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Trade command
    trade_parser = subparsers.add_parser('trade', help='Run live trading')
    trade_parser.add_argument('--dry-run', action='store_true', 
                             help='Run in dry-run mode (no real trades)')
    trade_parser.add_argument('--log-level', default='INFO',
                             choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                             help='Logging level')
    trade_parser.add_argument('-v', '--verbosity', action='count', default=0,
                             help='Increase verbosity')
    
    # Backtest command
    backtest_parser = subparsers.add_parser('backtest', help='Run backtesting')
    backtest_parser.add_argument('--timerange', 
                                help='Timerange for backtesting (e.g., 20240101-20240201)')
    backtest_parser.add_argument('--export', 
                                help='Export results (trades, signals)')
    backtest_parser.add_argument('--log-level', default='INFO',
                                choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download historical data')
    download_parser.add_argument('--days', type=int, default=30,
                                help='Number of days to download')
    download_parser.add_argument('--pairs', nargs='+',
                                help='Specific pairs to download')
    download_parser.add_argument('--log-level', default='INFO',
                                choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show bot status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'trade':
        run_market_maker(args)
    elif args.command == 'backtest':
        run_backtest(args)
    elif args.command == 'download':
        download_data(args)
    elif args.command == 'status':
        show_status()


if __name__ == "__main__":
    main()