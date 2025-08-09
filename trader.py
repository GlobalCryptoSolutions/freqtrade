import asyncio
import time
from typing import Dict, List, Optional, Tuple
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from dataclasses import dataclass
from logger import logger
from config import config
from token_analyzer import TokenAnalysis

@dataclass
class TradeResult:
    """Data class for trade execution results"""
    success: bool
    transaction_hash: str
    gas_used: int
    gas_price: int
    amount_in: int
    amount_out: int
    actual_price: float
    slippage: float
    error_message: str = ""

@dataclass
class Position:
    """Data class for tracking token positions"""
    token_address: str
    symbol: str
    amount: int
    buy_price: float
    buy_timestamp: int
    buy_tx_hash: str
    current_price: float
    profit_loss_percent: float
    stop_loss_price: float
    take_profit_price: float

class AutoTrader:
    """Automated token trading with gas optimization"""
    
    def __init__(self, chain: str = 'ethereum'):
        self.chain = chain
        self.w3 = Web3(Web3.HTTPProvider(config.get_rpc_url(chain)))
        
        # Add PoA middleware for BSC
        if chain == 'bsc':
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        # Setup account
        self.account = Account.from_key(config.PRIVATE_KEY)
        self.wallet_address = config.WALLET_ADDRESS
        
        # Router contracts
        self.routers = {
            'ethereum': {
                'uniswap_v2': config.UNISWAP_V2_ROUTER,
                'uniswap_v3': config.UNISWAP_V3_ROUTER
            },
            'bsc': {
                'pancakeswap_v2': config.PANCAKESWAP_ROUTER
            }
        }
        
        # Router ABI (simplified for swaps)
        self.router_abi = [
            {
                "inputs": [
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "amountOutMin", "type": "uint256"},
                    {"name": "path", "type": "address[]"},
                    {"name": "to", "type": "address"},
                    {"name": "deadline", "type": "uint256"}
                ],
                "name": "swapExactETHForTokens",
                "outputs": [{"name": "amounts", "type": "uint256[]"}],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "amountOutMin", "type": "uint256"},
                    {"name": "path", "type": "address[]"},
                    {"name": "to", "type": "address"},
                    {"name": "deadline", "type": "uint256"}
                ],
                "name": "swapExactTokensForETH",
                "outputs": [{"name": "amounts", "type": "uint256[]"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "amountOut", "type": "uint256"},
                    {"name": "path", "type": "address[]"}
                ],
                "name": "getAmountsIn",
                "outputs": [{"name": "amounts", "type": "uint256[]"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "path", "type": "address[]"}
                ],
                "name": "getAmountsOut",
                "outputs": [{"name": "amounts", "type": "uint256[]"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        # ERC20 ABI for approvals
        self.erc20_abi = config.ERC20_ABI + [
            {
                "inputs": [
                    {"name": "spender", "type": "address"},
                    {"name": "amount", "type": "uint256"}
                ],
                "name": "approve",
                "outputs": [{"name": "", "type": "bool"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "owner", "type": "address"},
                    {"name": "spender", "type": "address"}
                ],
                "name": "allowance",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        # Track positions
        self.positions: Dict[str, Position] = {}
        
        # WETH addresses
        self.weth_addresses = {
            'ethereum': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            'bsc': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'
        }
        
        logger.info(f"AutoTrader initialized for {chain}")
        logger.info(f"Wallet: {self.wallet_address}")
    
    async def buy_token(self, analysis: TokenAnalysis, amount_eth: float = None) -> Optional[TradeResult]:
        """Buy a token using ETH"""
        try:
            if amount_eth is None:
                amount_eth = config.DEFAULT_BUY_AMOUNT_ETH
            
            logger.info(f"🔄 Attempting to buy {analysis.symbol} with {amount_eth} ETH")
            
            # Get the appropriate router
            router_address = self._get_router_address('uniswap_v2')  # Default to V2
            if not router_address:
                logger.error("No router address found")
                return None
            
            router_contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(router_address),
                abi=self.router_abi
            )
            
            # Prepare swap parameters
            amount_in = self.w3.to_wei(amount_eth, 'ether')
            weth_address = self.weth_addresses[self.chain]
            path = [weth_address, analysis.token_address]
            deadline = int(time.time()) + 300  # 5 minutes from now
            
            # Calculate minimum amount out with slippage
            amounts_out = router_contract.functions.getAmountsOut(amount_in, path).call()
            expected_amount_out = amounts_out[-1]
            slippage_multiplier = (100 - config.DEFAULT_SLIPPAGE) / 100
            min_amount_out = int(expected_amount_out * slippage_multiplier)
            
            # Get optimized gas price
            gas_price = await self._get_optimized_gas_price()
            
            # Build transaction
            transaction = router_contract.functions.swapExactETHForTokens(
                min_amount_out,
                path,
                self.wallet_address,
                deadline
            ).build_transaction({
                'from': self.wallet_address,
                'value': amount_in,
                'gas': 200000,  # Estimated gas limit
                'gasPrice': gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address),
            })
            
            # Sign and send transaction
            signed_txn = self.account.sign_transaction(transaction)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logger.info(f"Buy transaction sent: {tx_hash.hex()}")
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt.status == 1:
                # Calculate actual amounts and slippage
                actual_amount_out = self._get_token_amount_from_receipt(receipt, analysis.token_address)
                actual_slippage = ((expected_amount_out - actual_amount_out) / expected_amount_out) * 100
                
                # Calculate buy price
                buy_price = amount_eth / (actual_amount_out / 10**analysis.decimals)
                
                # Create position
                position = Position(
                    token_address=analysis.token_address,
                    symbol=analysis.symbol,
                    amount=actual_amount_out,
                    buy_price=buy_price,
                    buy_timestamp=int(time.time()),
                    buy_tx_hash=tx_hash.hex(),
                    current_price=buy_price,
                    profit_loss_percent=0.0,
                    stop_loss_price=buy_price * (1 - config.STOP_LOSS_PERCENT / 100),
                    take_profit_price=buy_price * (1 + config.PROFIT_TARGET_PERCENT / 100)
                )
                
                self.positions[analysis.token_address] = position
                
                result = TradeResult(
                    success=True,
                    transaction_hash=tx_hash.hex(),
                    gas_used=receipt.gasUsed,
                    gas_price=gas_price,
                    amount_in=amount_in,
                    amount_out=actual_amount_out,
                    actual_price=buy_price,
                    slippage=actual_slippage
                )
                
                logger.info(f"✅ Buy successful! Got {actual_amount_out / 10**analysis.decimals:.6f} {analysis.symbol}")
                logger.info(f"   Price: {buy_price:.8f} ETH per token")
                logger.info(f"   Slippage: {actual_slippage:.2f}%")
                
                return result
            else:
                logger.error("Buy transaction failed")
                return TradeResult(
                    success=False,
                    transaction_hash=tx_hash.hex(),
                    gas_used=receipt.gasUsed,
                    gas_price=gas_price,
                    amount_in=amount_in,
                    amount_out=0,
                    actual_price=0,
                    slippage=0,
                    error_message="Transaction failed"
                )
                
        except Exception as e:
            logger.error(f"Error buying token {analysis.symbol}: {e}")
            return TradeResult(
                success=False,
                transaction_hash="",
                gas_used=0,
                gas_price=0,
                amount_in=0,
                amount_out=0,
                actual_price=0,
                slippage=0,
                error_message=str(e)
            )
    
    async def sell_token(self, token_address: str, amount: int = None) -> Optional[TradeResult]:
        """Sell a token for ETH"""
        try:
            if token_address not in self.positions:
                logger.error(f"No position found for token {token_address}")
                return None
            
            position = self.positions[token_address]
            
            if amount is None:
                amount = position.amount  # Sell entire position
            
            logger.info(f"🔄 Attempting to sell {amount / 10**18:.6f} {position.symbol}")
            
            # Get the appropriate router
            router_address = self._get_router_address('uniswap_v2')
            if not router_address:
                logger.error("No router address found")
                return None
            
            router_contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(router_address),
                abi=self.router_abi
            )
            
            # Check and approve token if needed
            await self._ensure_token_approval(token_address, router_address, amount)
            
            # Prepare swap parameters
            weth_address = self.weth_addresses[self.chain]
            path = [token_address, weth_address]
            deadline = int(time.time()) + 300
            
            # Calculate minimum ETH out with slippage
            amounts_out = router_contract.functions.getAmountsOut(amount, path).call()
            expected_eth_out = amounts_out[-1]
            slippage_multiplier = (100 - config.DEFAULT_SLIPPAGE) / 100
            min_eth_out = int(expected_eth_out * slippage_multiplier)
            
            # Get optimized gas price
            gas_price = await self._get_optimized_gas_price()
            
            # Build transaction
            transaction = router_contract.functions.swapExactTokensForETH(
                amount,
                min_eth_out,
                path,
                self.wallet_address,
                deadline
            ).build_transaction({
                'from': self.wallet_address,
                'gas': 200000,
                'gasPrice': gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address),
            })
            
            # Sign and send transaction
            signed_txn = self.account.sign_transaction(transaction)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logger.info(f"Sell transaction sent: {tx_hash.hex()}")
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt.status == 1:
                # Calculate actual amounts
                actual_eth_out = self._get_eth_amount_from_receipt(receipt)
                actual_slippage = ((expected_eth_out - actual_eth_out) / expected_eth_out) * 100
                
                # Calculate sell price and P&L
                sell_price = (actual_eth_out / 10**18) / (amount / 10**18)
                profit_loss = ((sell_price - position.buy_price) / position.buy_price) * 100
                
                # Update or remove position
                if amount == position.amount:
                    del self.positions[token_address]
                    logger.info(f"📈 Position closed with {profit_loss:.2f}% P&L")
                else:
                    position.amount -= amount
                
                result = TradeResult(
                    success=True,
                    transaction_hash=tx_hash.hex(),
                    gas_used=receipt.gasUsed,
                    gas_price=gas_price,
                    amount_in=amount,
                    amount_out=actual_eth_out,
                    actual_price=sell_price,
                    slippage=actual_slippage
                )
                
                logger.info(f"✅ Sell successful! Got {actual_eth_out / 10**18:.6f} ETH")
                logger.info(f"   Price: {sell_price:.8f} ETH per token")
                logger.info(f"   Slippage: {actual_slippage:.2f}%")
                
                return result
            else:
                logger.error("Sell transaction failed")
                return TradeResult(
                    success=False,
                    transaction_hash=tx_hash.hex(),
                    gas_used=receipt.gasUsed,
                    gas_price=gas_price,
                    amount_in=amount,
                    amount_out=0,
                    actual_price=0,
                    slippage=0,
                    error_message="Transaction failed"
                )
                
        except Exception as e:
            logger.error(f"Error selling token: {e}")
            return TradeResult(
                success=False,
                transaction_hash="",
                gas_used=0,
                gas_price=0,
                amount_in=0,
                amount_out=0,
                actual_price=0,
                slippage=0,
                error_message=str(e)
            )
    
    async def _ensure_token_approval(self, token_address: str, spender: str, amount: int):
        """Ensure token is approved for spending by the router"""
        try:
            token_contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(token_address),
                abi=self.erc20_abi
            )
            
            # Check current allowance
            allowance = token_contract.functions.allowance(self.wallet_address, spender).call()
            
            if allowance < amount:
                logger.info(f"Approving {token_address} for spending...")
                
                # Approve maximum amount
                max_approval = 2**256 - 1
                gas_price = await self._get_optimized_gas_price()
                
                approval_tx = token_contract.functions.approve(spender, max_approval).build_transaction({
                    'from': self.wallet_address,
                    'gas': 100000,
                    'gasPrice': gas_price,
                    'nonce': self.w3.eth.get_transaction_count(self.wallet_address),
                })
                
                signed_approval = self.account.sign_transaction(approval_tx)
                approval_hash = self.w3.eth.send_raw_transaction(signed_approval.rawTransaction)
                
                # Wait for approval confirmation
                approval_receipt = self.w3.eth.wait_for_transaction_receipt(approval_hash, timeout=60)
                
                if approval_receipt.status == 1:
                    logger.info("✅ Token approval successful")
                else:
                    raise Exception("Token approval failed")
                    
        except Exception as e:
            logger.error(f"Error approving token: {e}")
            raise
    
    async def _get_optimized_gas_price(self) -> int:
        """Get optimized gas price based on network conditions"""
        try:
            # Get current gas price
            current_gas_price = self.w3.eth.gas_price
            
            # Add premium for faster execution (20% increase)
            optimized_gas_price = int(current_gas_price * 1.2)
            
            # Cap at maximum configured gas price
            max_gas_price = self.w3.to_wei(config.MAX_GAS_PRICE_GWEI, 'gwei')
            final_gas_price = min(optimized_gas_price, max_gas_price)
            
            logger.debug(f"Gas price: {self.w3.from_wei(final_gas_price, 'gwei'):.2f} gwei")
            
            return final_gas_price
            
        except Exception as e:
            logger.error(f"Error getting gas price: {e}")
            # Fallback to default
            return self.w3.to_wei(20, 'gwei')
    
    def _get_router_address(self, dex: str) -> Optional[str]:
        """Get router address for the specified DEX"""
        return self.routers.get(self.chain, {}).get(dex)
    
    def _get_token_amount_from_receipt(self, receipt, token_address: str) -> int:
        """Extract token amount from transaction receipt"""
        # This is a simplified implementation
        # In practice, you would parse the Transfer events from the receipt
        return 0  # Placeholder
    
    def _get_eth_amount_from_receipt(self, receipt) -> int:
        """Extract ETH amount from transaction receipt"""
        # This is a simplified implementation
        # In practice, you would parse the Transfer events from the receipt
        return 0  # Placeholder
    
    def get_positions(self) -> Dict[str, Position]:
        """Get current positions"""
        return self.positions.copy()
    
    def get_position_value_eth(self, token_address: str) -> float:
        """Get current value of a position in ETH"""
        if token_address not in self.positions:
            return 0.0
        
        position = self.positions[token_address]
        # This would require getting current price from DEX
        # For now, return a placeholder
        return position.amount * position.current_price
    
    async def update_position_prices(self):
        """Update current prices for all positions"""
        for token_address, position in self.positions.items():
            try:
                # Get current price from DEX
                # This is a placeholder - you would implement actual price fetching
                current_price = position.buy_price  # Placeholder
                
                position.current_price = current_price
                position.profit_loss_percent = ((current_price - position.buy_price) / position.buy_price) * 100
                
            except Exception as e:
                logger.error(f"Error updating price for {position.symbol}: {e}")

# Example usage
async def execute_trade_on_analysis(analysis: TokenAnalysis):
    """Example function to execute a trade based on analysis"""
    if not analysis:
        return
    
    trader = AutoTrader(analysis.chain if hasattr(analysis, 'chain') else 'ethereum')
    
    # Only trade if token passes safety checks
    if trader_analyzer.is_token_safe(analysis):
        logger.info(f"🎯 Token {analysis.symbol} passed safety checks, executing buy...")
        
        trade_result = await trader.buy_token(analysis)
        
        if trade_result and trade_result.success:
            logger.info(f"✅ Successfully bought {analysis.symbol}")
        else:
            logger.error(f"❌ Failed to buy {analysis.symbol}")
    else:
        logger.warning(f"⚠️ Token {analysis.symbol} failed safety checks, skipping trade")

if __name__ == "__main__":
    # Test the trader
    async def test_trader():
        from token_analyzer import TokenAnalysis
        
        # Create a sample analysis for testing
        test_analysis = TokenAnalysis(
            token_address='0x1234567890123456789012345678901234567890',
            name='TestToken',
            symbol='TEST',
            decimals=18,
            total_supply=1000000000000000000000000,
            liquidity_eth=5.0,
            liquidity_usd=15000.0,
            market_cap=50000.0,
            buy_tax=0.0,
            sell_tax=0.0,
            is_honeypot=False,
            is_verified=True,
            owner_percentage=10.0,
            locked_percentage=80.0,
            risk_score=25.0,
            analysis_timestamp=int(time.time()),
            warnings=[],
            pair_address='0x1234567890123456789012345678901234567890'
        )
        
        await execute_trade_on_analysis(test_analysis)
    
    # Uncomment to test (requires valid wallet setup)
    # asyncio.run(test_trader())