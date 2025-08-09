import asyncio
import time
from typing import Dict, List, Optional, Callable
from web3 import Web3
from web3.exceptions import TransactionNotFound, BlockNotFound
from hexbytes import HexBytes
import json
from dataclasses import dataclass
from logger import logger
from config import config

@dataclass
class NewPairEvent:
    """Data class for new pair creation events"""
    token0: str
    token1: str
    pair_address: str
    block_number: int
    transaction_hash: str
    timestamp: int
    dex: str
    chain: str

class DEXMonitor:
    """Monitor DEX for new token pair creation events"""
    
    def __init__(self, chain: str = 'ethereum'):
        self.chain = chain
        self.w3 = Web3(Web3.HTTPProvider(config.get_rpc_url(chain)))
        self.is_running = False
        self.callbacks: List[Callable] = []
        
        # DEX factory addresses
        self.factories = {
            'ethereum': {
                'uniswap_v2': '0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f',
                'uniswap_v3': '0x1F98431c8aD98523631AE4a59f267346ea31F984',
                'sushiswap': '0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac'
            },
            'bsc': {
                'pancakeswap_v2': '0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73',
                'pancakeswap_v3': '0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865'
            }
        }
        
        # Pair creation event signatures
        self.PAIR_CREATED_TOPIC = '0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9'  # PairCreated(address,address,address,uint256)
        
        self.last_processed_block = self.w3.eth.block_number
        logger.info(f"DEX Monitor initialized for {chain} at block {self.last_processed_block}")
    
    def add_callback(self, callback: Callable[[NewPairEvent], None]):
        """Add a callback function to be called when new pairs are detected"""
        self.callbacks.append(callback)
        logger.info(f"Added callback: {callback.__name__}")
    
    async def get_new_pairs_from_block(self, block_number: int) -> List[NewPairEvent]:
        """Get new pair creation events from a specific block"""
        new_pairs = []
        
        try:
            # Get the block
            block = self.w3.eth.get_block(block_number, full_transactions=True)
            
            for tx in block.transactions:
                try:
                    # Get transaction receipt
                    receipt = self.w3.eth.get_transaction_receipt(tx.hash)
                    
                    # Check logs for PairCreated events
                    for log in receipt.logs:
                        if (len(log.topics) > 0 and 
                            log.topics[0].hex() == self.PAIR_CREATED_TOPIC and
                            log.address.lower() in [addr.lower() for factory_addrs in self.factories.get(self.chain, {}).values() for addr in [factory_addrs]]):
                            
                            # Decode the PairCreated event
                            pair_event = self._decode_pair_created_event(log, block.timestamp, self.chain)
                            if pair_event:
                                new_pairs.append(pair_event)
                                logger.info(f"New pair detected: {pair_event.token0[:8]}.../{pair_event.token1[:8]}... on {pair_event.dex}")
                
                except Exception as e:
                    logger.debug(f"Error processing transaction {tx.hash.hex()}: {e}")
                    continue
                    
        except BlockNotFound:
            logger.warning(f"Block {block_number} not found")
        except Exception as e:
            logger.error(f"Error processing block {block_number}: {e}")
        
        return new_pairs
    
    def _decode_pair_created_event(self, log, timestamp: int, chain: str) -> Optional[NewPairEvent]:
        """Decode a PairCreated event log"""
        try:
            # PairCreated event structure: PairCreated(address indexed token0, address indexed token1, address pair, uint256)
            if len(log.topics) < 3:
                return None
            
            token0 = self.w3.to_checksum_address('0x' + log.topics[1].hex()[26:])
            token1 = self.w3.to_checksum_address('0x' + log.topics[2].hex()[26:])
            
            # Decode pair address from data
            if len(log.data) < 64:
                return None
            
            pair_address = self.w3.to_checksum_address('0x' + log.data[26:66].hex())
            
            # Determine which DEX this is from
            dex_name = self._get_dex_name(log.address, chain)
            
            return NewPairEvent(
                token0=token0,
                token1=token1,
                pair_address=pair_address,
                block_number=log.blockNumber,
                transaction_hash=log.transactionHash.hex(),
                timestamp=timestamp,
                dex=dex_name,
                chain=chain
            )
            
        except Exception as e:
            logger.error(f"Error decoding PairCreated event: {e}")
            return None
    
    def _get_dex_name(self, factory_address: str, chain: str) -> str:
        """Get DEX name from factory address"""
        factory_address = factory_address.lower()
        
        for dex_name, address in self.factories.get(chain, {}).items():
            if address.lower() == factory_address:
                return dex_name
        
        return "unknown"
    
    async def monitor_new_pairs(self):
        """Main monitoring loop for new pair creation events"""
        logger.info("Starting DEX monitoring...")
        self.is_running = True
        
        while self.is_running:
            try:
                current_block = self.w3.eth.block_number
                
                # Process new blocks
                if current_block > self.last_processed_block:
                    logger.debug(f"Processing blocks {self.last_processed_block + 1} to {current_block}")
                    
                    # Process each new block
                    for block_num in range(self.last_processed_block + 1, current_block + 1):
                        new_pairs = await self.get_new_pairs_from_block(block_num)
                        
                        # Call callbacks for each new pair
                        for pair in new_pairs:
                            for callback in self.callbacks:
                                try:
                                    await callback(pair) if asyncio.iscoroutinefunction(callback) else callback(pair)
                                except Exception as e:
                                    logger.error(f"Error in callback {callback.__name__}: {e}")
                    
                    self.last_processed_block = current_block
                
                # Wait before checking again
                await asyncio.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    def stop(self):
        """Stop the monitoring process"""
        logger.info("Stopping DEX monitoring...")
        self.is_running = False

class MultiChainDEXMonitor:
    """Monitor multiple chains simultaneously"""
    
    def __init__(self, chains: List[str] = None):
        if chains is None:
            chains = ['ethereum', 'bsc']
        
        self.monitors = {}
        self.callbacks: List[Callable] = []
        
        for chain in chains:
            try:
                monitor = DEXMonitor(chain)
                self.monitors[chain] = monitor
                logger.info(f"Initialized monitor for {chain}")
            except Exception as e:
                logger.error(f"Failed to initialize monitor for {chain}: {e}")
    
    def add_callback(self, callback: Callable[[NewPairEvent], None]):
        """Add callback to all monitors"""
        self.callbacks.append(callback)
        for monitor in self.monitors.values():
            monitor.add_callback(callback)
    
    async def start_monitoring(self):
        """Start monitoring all chains"""
        tasks = []
        for chain, monitor in self.monitors.items():
            task = asyncio.create_task(monitor.monitor_new_pairs())
            tasks.append(task)
            logger.info(f"Started monitoring {chain}")
        
        # Wait for all monitoring tasks
        await asyncio.gather(*tasks)
    
    def stop_all(self):
        """Stop monitoring all chains"""
        for monitor in self.monitors.values():
            monitor.stop()

# Example usage and testing
async def example_callback(pair_event: NewPairEvent):
    """Example callback function for new pair events"""
    logger.info(f"🚀 NEW PAIR DETECTED!")
    logger.info(f"   DEX: {pair_event.dex}")
    logger.info(f"   Chain: {pair_event.chain}")
    logger.info(f"   Token0: {pair_event.token0}")
    logger.info(f"   Token1: {pair_event.token1}")
    logger.info(f"   Pair: {pair_event.pair_address}")
    logger.info(f"   Block: {pair_event.block_number}")
    logger.info(f"   TxHash: {pair_event.transaction_hash}")

if __name__ == "__main__":
    # Test the monitor
    async def test_monitor():
        monitor = MultiChainDEXMonitor(['ethereum'])
        monitor.add_callback(example_callback)
        await monitor.start_monitoring()
    
    asyncio.run(test_monitor())