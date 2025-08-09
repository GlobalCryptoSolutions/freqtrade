import asyncio
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from logger import logger
from config import config
from trader import AutoTrader, Position, TradeResult
from token_analyzer import TokenAnalyzer

@dataclass
class RiskEvent:
    """Data class for risk management events"""
    event_type: str  # 'stop_loss', 'take_profit', 'position_update'
    token_address: str
    symbol: str
    current_price: float
    trigger_price: float
    profit_loss_percent: float
    timestamp: int
    action_taken: str

class RiskManager:
    """Risk management system for monitoring and managing positions"""
    
    def __init__(self, trader: AutoTrader):
        self.trader = trader
        self.analyzer = TokenAnalyzer(trader.chain)
        self.is_running = False
        self.callbacks: List[Callable] = []
        
        # Risk parameters
        self.max_position_size_eth = config.DEFAULT_BUY_AMOUNT_ETH * 5  # Max 5x normal buy amount
        self.max_total_exposure_eth = config.DEFAULT_BUY_AMOUNT_ETH * 10  # Max total exposure
        self.max_loss_per_trade_percent = config.STOP_LOSS_PERCENT
        self.max_daily_loss_percent = 20.0  # Max 20% daily loss
        
        # Tracking
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.last_reset_day = time.strftime('%Y-%m-%d')
        
        logger.info("Risk Manager initialized")
    
    def add_callback(self, callback: Callable[[RiskEvent], None]):
        """Add a callback function for risk events"""
        self.callbacks.append(callback)
    
    async def start_monitoring(self):
        """Start the risk monitoring loop"""
        logger.info("Starting risk monitoring...")
        self.is_running = True
        
        while self.is_running:
            try:
                await self._check_daily_reset()
                await self._monitor_positions()
                await self._check_overall_risk()
                
                # Sleep before next check
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in risk monitoring loop: {e}")
                await asyncio.sleep(30)  # Wait longer on error
    
    def stop(self):
        """Stop risk monitoring"""
        logger.info("Stopping risk monitoring...")
        self.is_running = False
    
    async def _check_daily_reset(self):
        """Reset daily counters if new day"""
        current_day = time.strftime('%Y-%m-%d')
        if current_day != self.last_reset_day:
            logger.info(f"New day detected, resetting daily counters")
            logger.info(f"Previous day P&L: {self.daily_pnl:.4f} ETH ({self.daily_trades} trades)")
            
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.last_reset_day = current_day
    
    async def _monitor_positions(self):
        """Monitor all positions for stop-loss and take-profit triggers"""
        positions = self.trader.get_positions()
        
        for token_address, position in positions.items():
            try:
                # Update current price
                current_price = await self._get_current_token_price(token_address, position)
                if current_price is None:
                    continue
                
                # Update position
                position.current_price = current_price
                old_pnl = position.profit_loss_percent
                position.profit_loss_percent = ((current_price - position.buy_price) / position.buy_price) * 100
                
                # Check for stop-loss trigger
                if current_price <= position.stop_loss_price:
                    await self._execute_stop_loss(position)
                
                # Check for take-profit trigger
                elif current_price >= position.take_profit_price:
                    await self._execute_take_profit(position)
                
                # Check for trailing stop-loss update
                elif position.profit_loss_percent > 20:  # If up 20%, update stop-loss
                    await self._update_trailing_stop_loss(position)
                
                # Log significant price changes
                if abs(position.profit_loss_percent - old_pnl) > 5:  # 5% change
                    logger.info(f"📊 {position.symbol}: {position.profit_loss_percent:.2f}% P&L")
                
                # Create position update event
                event = RiskEvent(
                    event_type='position_update',
                    token_address=token_address,
                    symbol=position.symbol,
                    current_price=current_price,
                    trigger_price=0,
                    profit_loss_percent=position.profit_loss_percent,
                    timestamp=int(time.time()),
                    action_taken='none'
                )
                
                await self._notify_callbacks(event)
                
            except Exception as e:
                logger.error(f"Error monitoring position {position.symbol}: {e}")
    
    async def _execute_stop_loss(self, position: Position):
        """Execute stop-loss for a position"""
        try:
            logger.warning(f"🛑 STOP-LOSS TRIGGERED for {position.symbol}")
            logger.warning(f"   Current Price: {position.current_price:.8f} ETH")
            logger.warning(f"   Stop-Loss Price: {position.stop_loss_price:.8f} ETH")
            logger.warning(f"   P&L: {position.profit_loss_percent:.2f}%")
            
            # Execute sell order
            trade_result = await self.trader.sell_token(position.token_address)
            
            if trade_result and trade_result.success:
                loss_eth = position.buy_price * (position.amount / 10**18) - (trade_result.amount_out / 10**18)
                self.daily_pnl -= loss_eth
                self.daily_trades += 1
                
                # Create risk event
                event = RiskEvent(
                    event_type='stop_loss',
                    token_address=position.token_address,
                    symbol=position.symbol,
                    current_price=position.current_price,
                    trigger_price=position.stop_loss_price,
                    profit_loss_percent=position.profit_loss_percent,
                    timestamp=int(time.time()),
                    action_taken='sold_position'
                )
                
                await self._notify_callbacks(event)
                logger.info(f"✅ Stop-loss executed successfully")
                
            else:
                logger.error(f"❌ Failed to execute stop-loss for {position.symbol}")
                
        except Exception as e:
            logger.error(f"Error executing stop-loss for {position.symbol}: {e}")
    
    async def _execute_take_profit(self, position: Position):
        """Execute take-profit for a position"""
        try:
            logger.info(f"🎯 TAKE-PROFIT TRIGGERED for {position.symbol}")
            logger.info(f"   Current Price: {position.current_price:.8f} ETH")
            logger.info(f"   Take-Profit Price: {position.take_profit_price:.8f} ETH")
            logger.info(f"   P&L: {position.profit_loss_percent:.2f}%")
            
            # Execute sell order
            trade_result = await self.trader.sell_token(position.token_address)
            
            if trade_result and trade_result.success:
                profit_eth = (trade_result.amount_out / 10**18) - position.buy_price * (position.amount / 10**18)
                self.daily_pnl += profit_eth
                self.daily_trades += 1
                
                # Create risk event
                event = RiskEvent(
                    event_type='take_profit',
                    token_address=position.token_address,
                    symbol=position.symbol,
                    current_price=position.current_price,
                    trigger_price=position.take_profit_price,
                    profit_loss_percent=position.profit_loss_percent,
                    timestamp=int(time.time()),
                    action_taken='sold_position'
                )
                
                await self._notify_callbacks(event)
                logger.info(f"✅ Take-profit executed successfully")
                
            else:
                logger.error(f"❌ Failed to execute take-profit for {position.symbol}")
                
        except Exception as e:
            logger.error(f"Error executing take-profit for {position.symbol}: {e}")
    
    async def _update_trailing_stop_loss(self, position: Position):
        """Update trailing stop-loss for profitable positions"""
        try:
            # Calculate new stop-loss price (e.g., 15% below current price if up 20%+)
            trailing_stop_percent = 15.0
            new_stop_loss = position.current_price * (1 - trailing_stop_percent / 100)
            
            # Only update if new stop-loss is higher than current
            if new_stop_loss > position.stop_loss_price:
                old_stop_loss = position.stop_loss_price
                position.stop_loss_price = new_stop_loss
                
                logger.info(f"📈 Updated trailing stop-loss for {position.symbol}")
                logger.info(f"   Old Stop-Loss: {old_stop_loss:.8f} ETH")
                logger.info(f"   New Stop-Loss: {new_stop_loss:.8f} ETH")
                
        except Exception as e:
            logger.error(f"Error updating trailing stop-loss for {position.symbol}: {e}")
    
    async def _check_overall_risk(self):
        """Check overall portfolio risk"""
        try:
            positions = self.trader.get_positions()
            
            # Calculate total exposure
            total_exposure = sum(
                position.buy_price * (position.amount / 10**18) 
                for position in positions.values()
            )
            
            # Check daily loss limit
            daily_loss_percent = (abs(self.daily_pnl) / max(total_exposure, 0.01)) * 100
            if self.daily_pnl < 0 and daily_loss_percent > self.max_daily_loss_percent:
                logger.warning(f"⚠️ Daily loss limit exceeded: {daily_loss_percent:.2f}%")
                await self._emergency_close_all_positions("daily_loss_limit")
            
            # Check total exposure
            if total_exposure > self.max_total_exposure_eth:
                logger.warning(f"⚠️ Total exposure limit exceeded: {total_exposure:.4f} ETH")
                # Could implement position size reduction here
            
            # Log daily stats periodically
            current_minute = int(time.time()) // 60
            if current_minute % 10 == 0:  # Every 10 minutes
                logger.debug(f"💰 Daily P&L: {self.daily_pnl:.4f} ETH | Trades: {self.daily_trades} | Exposure: {total_exposure:.4f} ETH")
                
        except Exception as e:
            logger.error(f"Error checking overall risk: {e}")
    
    async def _emergency_close_all_positions(self, reason: str):
        """Emergency close all positions"""
        try:
            logger.critical(f"🚨 EMERGENCY: Closing all positions due to {reason}")
            
            positions = self.trader.get_positions().copy()
            for token_address, position in positions.items():
                try:
                    trade_result = await self.trader.sell_token(token_address)
                    if trade_result and trade_result.success:
                        logger.info(f"✅ Emergency closed position in {position.symbol}")
                    else:
                        logger.error(f"❌ Failed to emergency close {position.symbol}")
                except Exception as e:
                    logger.error(f"Error emergency closing {position.symbol}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in emergency close all positions: {e}")
    
    async def _get_current_token_price(self, token_address: str, position: Position) -> Optional[float]:
        """Get current token price in ETH"""
        try:
            # This is a simplified implementation
            # In practice, you would query the DEX for current price
            
            # For now, simulate price movement (in a real implementation, 
            # you would query the actual DEX pair)
            import random
            
            # Simulate some price volatility around the buy price
            volatility = 0.1  # 10% volatility
            price_change = (random.random() - 0.5) * 2 * volatility
            current_price = position.buy_price * (1 + price_change)
            
            return max(current_price, 0.000001)  # Ensure price doesn't go negative
            
        except Exception as e:
            logger.error(f"Error getting current price for {token_address}: {e}")
            return None
    
    async def _notify_callbacks(self, event: RiskEvent):
        """Notify all callbacks about a risk event"""
        for callback in self.callbacks:
            try:
                await callback(event) if asyncio.iscoroutinefunction(callback) else callback(event)
            except Exception as e:
                logger.error(f"Error in risk callback: {e}")
    
    def should_allow_new_trade(self, analysis) -> bool:
        """Check if a new trade should be allowed based on risk parameters"""
        try:
            positions = self.trader.get_positions()
            
            # Check daily loss limit
            if self.daily_pnl < 0:
                daily_loss_percent = abs(self.daily_pnl) / max(config.DEFAULT_BUY_AMOUNT_ETH, 0.01) * 100
                if daily_loss_percent > self.max_daily_loss_percent:
                    logger.warning(f"⚠️ New trade blocked: Daily loss limit exceeded")
                    return False
            
            # Check total exposure
            total_exposure = sum(
                position.buy_price * (position.amount / 10**18) 
                for position in positions.values()
            )
            
            if total_exposure + config.DEFAULT_BUY_AMOUNT_ETH > self.max_total_exposure_eth:
                logger.warning(f"⚠️ New trade blocked: Total exposure limit would be exceeded")
                return False
            
            # Check maximum number of positions
            if len(positions) >= 10:  # Max 10 concurrent positions
                logger.warning(f"⚠️ New trade blocked: Maximum positions limit reached")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if new trade should be allowed: {e}")
            return False
    
    def get_risk_stats(self) -> Dict:
        """Get current risk statistics"""
        positions = self.trader.get_positions()
        
        total_exposure = sum(
            position.buy_price * (position.amount / 10**18) 
            for position in positions.values()
        )
        
        return {
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'total_exposure': total_exposure,
            'active_positions': len(positions),
            'max_daily_loss_percent': self.max_daily_loss_percent,
            'max_total_exposure_eth': self.max_total_exposure_eth
        }

# Example risk event callback
async def risk_event_logger(event: RiskEvent):
    """Example callback for logging risk events"""
    if event.event_type == 'stop_loss':
        logger.warning(f"🛑 Stop-loss executed: {event.symbol} at {event.profit_loss_percent:.2f}% loss")
    elif event.event_type == 'take_profit':
        logger.info(f"🎯 Take-profit executed: {event.symbol} at {event.profit_loss_percent:.2f}% profit")
    elif event.event_type == 'position_update':
        if abs(event.profit_loss_percent) > 10:  # Only log significant moves
            logger.debug(f"📊 {event.symbol}: {event.profit_loss_percent:.1f}% P&L")

if __name__ == "__main__":
    # Test risk manager
    async def test_risk_manager():
        from trader import AutoTrader
        
        trader = AutoTrader('ethereum')
        risk_manager = RiskManager(trader)
        risk_manager.add_callback(risk_event_logger)
        
        # Start monitoring (this would run indefinitely in practice)
        await risk_manager.start_monitoring()
    
    # Uncomment to test
    # asyncio.run(test_risk_manager())