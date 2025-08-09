#!/usr/bin/env python3
"""
Meme Coin Sniper Bot
A comprehensive bot for monitoring and trading new token listings on DEXs
"""

import asyncio
import signal
import sys
import time
from typing import Dict, List, Optional
from dataclasses import dataclass

# Import our modules
from logger import logger
from config import config
from dex_monitor import MultiChainDEXMonitor, NewPairEvent
from token_analyzer import TokenAnalyzer, TokenAnalysis, analyze_new_pair
from trader import AutoTrader
from risk_manager import RiskManager, RiskEvent

@dataclass
class BotStats:
    """Bot statistics tracking"""
    start_time: int
    pairs_detected: int
    tokens_analyzed: int
    trades_executed: int
    successful_trades: int
    total_profit_loss: float
    best_trade_profit: float
    worst_trade_loss: float

class MemeCoinSniperBot:
    """Main meme coin sniper bot class"""
    
    def __init__(self, chains: List[str] = None):
        """Initialize the sniper bot"""
        logger.info("🤖 Initializing Meme Coin Sniper Bot...")
        
        # Validate configuration
        if not config.validate_config():
            logger.error("❌ Configuration validation failed")
            sys.exit(1)
        
        # Initialize chains
        if chains is None:
            chains = ['ethereum']  # Default to Ethereum only
        
        self.chains = chains
        
        # Initialize components
        self.dex_monitor = MultiChainDEXMonitor(chains)
        self.traders = {chain: AutoTrader(chain) for chain in chains}
        self.analyzers = {chain: TokenAnalyzer(chain) for chain in chains}
        self.risk_managers = {chain: RiskManager(self.traders[chain]) for chain in chains}
        
        # Bot state
        self.is_running = False
        self.stats = BotStats(
            start_time=int(time.time()),
            pairs_detected=0,
            tokens_analyzed=0,
            trades_executed=0,
            successful_trades=0,
            total_profit_loss=0.0,
            best_trade_profit=0.0,
            worst_trade_loss=0.0
        )
        
        # Setup callbacks
        self._setup_callbacks()
        
        logger.info(f"✅ Bot initialized for chains: {', '.join(chains)}")
        logger.info(f"💰 Default buy amount: {config.DEFAULT_BUY_AMOUNT_ETH} ETH")
        logger.info(f"📊 Risk settings: {config.STOP_LOSS_PERCENT}% stop-loss, {config.PROFIT_TARGET_PERCENT}% take-profit")
    
    def _setup_callbacks(self):
        """Setup callbacks for various events"""
        # DEX monitoring callbacks
        self.dex_monitor.add_callback(self._on_new_pair_detected)
        
        # Risk management callbacks
        for risk_manager in self.risk_managers.values():
            risk_manager.add_callback(self._on_risk_event)
    
    async def _on_new_pair_detected(self, pair_event: NewPairEvent):
        """Handle new pair detection"""
        try:
            self.stats.pairs_detected += 1
            
            logger.info(f"🚀 NEW PAIR DETECTED!")
            logger.info(f"   DEX: {pair_event.dex}")
            logger.info(f"   Chain: {pair_event.chain}")
            logger.info(f"   Pair: {pair_event.pair_address}")
            logger.info(f"   Block: {pair_event.block_number}")
            
            # Analyze the token
            analyzer = self.analyzers.get(pair_event.chain)
            if not analyzer:
                logger.warning(f"No analyzer available for chain {pair_event.chain}")
                return
            
            analysis = await analyzer.analyze_token(pair_event)
            if not analysis:
                logger.warning(f"Failed to analyze token in pair {pair_event.pair_address}")
                return
            
            self.stats.tokens_analyzed += 1
            
            # Log analysis results
            logger.info(f"📊 ANALYSIS COMPLETE: {analysis.symbol}")
            logger.info(f"   Risk Score: {analysis.risk_score}/100")
            logger.info(f"   Liquidity: {analysis.liquidity_eth:.3f} ETH (${analysis.liquidity_usd:.0f})")
            logger.info(f"   Market Cap: ${analysis.market_cap:.0f}")
            
            if analysis.warnings:
                logger.warning(f"   ⚠️ Warnings: {', '.join(analysis.warnings)}")
            
            # Check if we should trade
            risk_manager = self.risk_managers.get(pair_event.chain)
            trader = self.traders.get(pair_event.chain)
            
            if not risk_manager or not trader:
                logger.warning(f"Missing risk manager or trader for chain {pair_event.chain}")
                return
            
            # Risk checks
            if not risk_manager.should_allow_new_trade(analysis):
                logger.warning(f"⚠️ Risk manager blocked trade for {analysis.symbol}")
                return
            
            # Safety checks
            if not analyzer.is_token_safe(analysis):
                logger.warning(f"⚠️ Token {analysis.symbol} failed safety checks, skipping")
                return
            
            # Execute trade
            logger.info(f"🎯 Token {analysis.symbol} passed all checks, executing trade...")
            await self._execute_trade(analysis, trader)
            
        except Exception as e:
            logger.error(f"Error handling new pair: {e}")
    
    async def _execute_trade(self, analysis: TokenAnalysis, trader: AutoTrader):
        """Execute a trade based on analysis"""
        try:
            self.stats.trades_executed += 1
            
            # Execute buy order
            trade_result = await trader.buy_token(analysis)
            
            if trade_result and trade_result.success:
                self.stats.successful_trades += 1
                
                logger.info(f"✅ TRADE EXECUTED SUCCESSFULLY!")
                logger.info(f"   Token: {analysis.symbol}")
                logger.info(f"   Amount: {trade_result.amount_out / 10**analysis.decimals:.6f} {analysis.symbol}")
                logger.info(f"   Price: {trade_result.actual_price:.8f} ETH")
                logger.info(f"   Slippage: {trade_result.slippage:.2f}%")
                logger.info(f"   Gas Used: {trade_result.gas_used:,}")
                logger.info(f"   Tx: {trade_result.transaction_hash}")
                
                # Send notification if configured
                await self._send_notification(f"✅ Bought {analysis.symbol} for {config.DEFAULT_BUY_AMOUNT_ETH} ETH")
                
            else:
                error_msg = trade_result.error_message if trade_result else "Unknown error"
                logger.error(f"❌ TRADE FAILED: {error_msg}")
                
                # Send notification if configured
                await self._send_notification(f"❌ Failed to buy {analysis.symbol}: {error_msg}")
                
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
    
    async def _on_risk_event(self, event: RiskEvent):
        """Handle risk management events"""
        try:
            if event.event_type == 'stop_loss':
                self.stats.worst_trade_loss = min(self.stats.worst_trade_loss, event.profit_loss_percent)
                self.stats.total_profit_loss += event.profit_loss_percent
                
                await self._send_notification(
                    f"🛑 Stop-loss executed: {event.symbol} at {event.profit_loss_percent:.2f}% loss"
                )
                
            elif event.event_type == 'take_profit':
                self.stats.best_trade_profit = max(self.stats.best_trade_profit, event.profit_loss_percent)
                self.stats.total_profit_loss += event.profit_loss_percent
                
                await self._send_notification(
                    f"🎯 Take-profit executed: {event.symbol} at {event.profit_loss_percent:.2f}% profit"
                )
                
        except Exception as e:
            logger.error(f"Error handling risk event: {e}")
    
    async def _send_notification(self, message: str):
        """Send notification via Telegram if configured"""
        try:
            if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
                # Import here to avoid dependency if not used
                from telegram import Bot
                
                bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
                await bot.send_message(
                    chat_id=config.TELEGRAM_CHAT_ID,
                    text=message,
                    parse_mode='HTML'
                )
                
        except Exception as e:
            logger.debug(f"Failed to send Telegram notification: {e}")
    
    async def start(self):
        """Start the bot"""
        try:
            logger.info("🚀 Starting Meme Coin Sniper Bot...")
            self.is_running = True
            
            # Start all components
            tasks = []
            
            # Start DEX monitoring
            monitor_task = asyncio.create_task(self.dex_monitor.start_monitoring())
            tasks.append(monitor_task)
            
            # Start risk managers
            for chain, risk_manager in self.risk_managers.items():
                risk_task = asyncio.create_task(risk_manager.start_monitoring())
                tasks.append(risk_task)
                logger.info(f"✅ Started risk monitoring for {chain}")
            
            # Start stats reporting
            stats_task = asyncio.create_task(self._stats_reporter())
            tasks.append(stats_task)
            
            logger.info("🎯 Bot is now running and monitoring for new tokens...")
            logger.info("Press Ctrl+C to stop the bot")
            
            # Wait for all tasks
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            await self.stop()
    
    async def stop(self):
        """Stop the bot"""
        try:
            logger.info("🛑 Stopping Meme Coin Sniper Bot...")
            self.is_running = False
            
            # Stop all components
            self.dex_monitor.stop_all()
            
            for risk_manager in self.risk_managers.values():
                risk_manager.stop()
            
            # Print final stats
            await self._print_final_stats()
            
            logger.info("✅ Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
    
    async def _stats_reporter(self):
        """Periodically report bot statistics"""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # Report every 5 minutes
                await self._print_stats()
                
            except Exception as e:
                logger.error(f"Error in stats reporter: {e}")
                await asyncio.sleep(60)
    
    async def _print_stats(self):
        """Print current bot statistics"""
        try:
            runtime = int(time.time()) - self.stats.start_time
            runtime_hours = runtime // 3600
            runtime_minutes = (runtime % 3600) // 60
            
            logger.info("📊 BOT STATISTICS")
            logger.info(f"   Runtime: {runtime_hours}h {runtime_minutes}m")
            logger.info(f"   Pairs Detected: {self.stats.pairs_detected}")
            logger.info(f"   Tokens Analyzed: {self.stats.tokens_analyzed}")
            logger.info(f"   Trades Executed: {self.stats.trades_executed}")
            logger.info(f"   Successful Trades: {self.stats.successful_trades}")
            
            if self.stats.trades_executed > 0:
                success_rate = (self.stats.successful_trades / self.stats.trades_executed) * 100
                logger.info(f"   Success Rate: {success_rate:.1f}%")
            
            # Risk manager stats
            for chain, risk_manager in self.risk_managers.items():
                risk_stats = risk_manager.get_risk_stats()
                logger.info(f"   {chain.title()} - Daily P&L: {risk_stats['daily_pnl']:.4f} ETH")
                logger.info(f"   {chain.title()} - Active Positions: {risk_stats['active_positions']}")
                
        except Exception as e:
            logger.error(f"Error printing stats: {e}")
    
    async def _print_final_stats(self):
        """Print final statistics when bot stops"""
        try:
            logger.info("📊 FINAL BOT STATISTICS")
            await self._print_stats()
            
            if self.stats.best_trade_profit > 0:
                logger.info(f"   Best Trade: +{self.stats.best_trade_profit:.2f}%")
            
            if self.stats.worst_trade_loss < 0:
                logger.info(f"   Worst Trade: {self.stats.worst_trade_loss:.2f}%")
                
        except Exception as e:
            logger.error(f"Error printing final stats: {e}")

def signal_handler(signum, frame):
    """Handle interrupt signals"""
    logger.info("\n🛑 Received interrupt signal, stopping bot...")
    sys.exit(0)

async def main():
    """Main function"""
    try:
        # Setup signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Print banner
        print("""
╔══════════════════════════════════════════════════════════════╗
║                   MEME COIN SNIPER BOT                      ║
║                     Version 1.0.0                          ║
║                                                            ║
║  🎯 Automated meme coin detection and trading              ║
║  📊 Risk management and position monitoring                ║
║  ⚡ Lightning-fast execution with gas optimization         ║
║                                                            ║
║  ⚠️  USE AT YOUR OWN RISK - NOT FINANCIAL ADVICE           ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
        # Initialize and start bot
        chains = ['ethereum']  # Can be extended to ['ethereum', 'bsc']
        bot = MemeCoinSniperBot(chains)
        
        try:
            await bot.start()
        except KeyboardInterrupt:
            logger.info("\n🛑 Keyboard interrupt received")
        finally:
            await bot.stop()
            
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)