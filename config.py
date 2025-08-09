import os
from dotenv import load_dotenv
from typing import Dict, Any
import logging

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the meme coin sniper bot"""
    
    def __init__(self):
        self.load_config()
    
    def load_config(self):
        """Load configuration from environment variables"""
        
        # Blockchain Configuration
        self.ETHEREUM_RPC_URL = os.getenv('ETHEREUM_RPC_URL', 'https://mainnet.infura.io/v3/YOUR_INFURA_KEY')
        self.BSC_RPC_URL = os.getenv('BSC_RPC_URL', 'https://bsc-dataseed.binance.org/')
        self.POLYGON_RPC_URL = os.getenv('POLYGON_RPC_URL', 'https://polygon-rpc.com/')
        self.ARBITRUM_RPC_URL = os.getenv('ARBITRUM_RPC_URL', 'https://arb1.arbitrum.io/rpc')
        
        # Wallet Configuration
        self.PRIVATE_KEY = os.getenv('PRIVATE_KEY', '')
        self.WALLET_ADDRESS = os.getenv('WALLET_ADDRESS', '')
        
        # Trading Configuration
        self.DEFAULT_BUY_AMOUNT_ETH = float(os.getenv('DEFAULT_BUY_AMOUNT_ETH', '0.01'))
        self.DEFAULT_SLIPPAGE = int(os.getenv('DEFAULT_SLIPPAGE', '5'))
        self.MAX_GAS_PRICE_GWEI = int(os.getenv('MAX_GAS_PRICE_GWEI', '50'))
        self.PROFIT_TARGET_PERCENT = float(os.getenv('PROFIT_TARGET_PERCENT', '50'))
        self.STOP_LOSS_PERCENT = float(os.getenv('STOP_LOSS_PERCENT', '30'))
        
        # DEX Configuration
        self.UNISWAP_V2_ROUTER = os.getenv('UNISWAP_V2_ROUTER', '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D')
        self.UNISWAP_V3_ROUTER = os.getenv('UNISWAP_V3_ROUTER', '0xE592427A0AEce92De3Edee1F18E0157C05861564')
        self.PANCAKESWAP_ROUTER = os.getenv('PANCAKESWAP_ROUTER', '0x10ED43C718714eb63d5aA57B78B54704E256024E')
        
        # Monitoring Configuration
        self.MONITOR_UNISWAP = os.getenv('MONITOR_UNISWAP', 'true').lower() == 'true'
        self.MONITOR_PANCAKESWAP = os.getenv('MONITOR_PANCAKESWAP', 'true').lower() == 'true'
        self.MONITOR_SUSHISWAP = os.getenv('MONITOR_SUSHISWAP', 'false').lower() == 'true'
        
        # Risk Management
        self.MIN_LIQUIDITY_ETH = float(os.getenv('MIN_LIQUIDITY_ETH', '1.0'))
        self.MAX_BUY_TAX = float(os.getenv('MAX_BUY_TAX', '10'))
        self.MAX_SELL_TAX = float(os.getenv('MAX_SELL_TAX', '10'))
        self.ENABLE_HONEYPOT_CHECK = os.getenv('ENABLE_HONEYPOT_CHECK', 'true').lower() == 'true'
        
        # Telegram Bot (optional)
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
        
        # Logging
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_TO_FILE = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
        
        # Contract ABIs
        self.UNISWAP_V2_FACTORY_ABI = [
            {
                "constant": True,
                "inputs": [{"name": "tokenA", "type": "address"}, {"name": "tokenB", "type": "address"}],
                "name": "getPair",
                "outputs": [{"name": "pair", "type": "address"}],
                "type": "function"
            }
        ]
        
        self.UNISWAP_V2_PAIR_ABI = [
            {
                "constant": True,
                "inputs": [],
                "name": "getReserves",
                "outputs": [
                    {"name": "_reserve0", "type": "uint112"},
                    {"name": "_reserve1", "type": "uint112"},
                    {"name": "_blockTimestampLast", "type": "uint32"}
                ],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "token0",
                "outputs": [{"name": "", "type": "address"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "token1",
                "outputs": [{"name": "", "type": "address"}],
                "type": "function"
            }
        ]
        
        self.ERC20_ABI = [
            {
                "constant": True,
                "inputs": [],
                "name": "name",
                "outputs": [{"name": "", "type": "string"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "totalSupply",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }
        ]
        
    def validate_config(self) -> bool:
        """Validate that required configuration is present"""
        required_fields = [
            'PRIVATE_KEY',
            'WALLET_ADDRESS',
            'ETHEREUM_RPC_URL'
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(self, field) or getattr(self, field) == f'your_{field.lower()}_here':
                missing_fields.append(field)
        
        if missing_fields:
            logging.error(f"Missing required configuration fields: {', '.join(missing_fields)}")
            return False
        
        return True
    
    def get_rpc_url(self, chain: str) -> str:
        """Get RPC URL for a specific chain"""
        chain_urls = {
            'ethereum': self.ETHEREUM_RPC_URL,
            'bsc': self.BSC_RPC_URL,
            'polygon': self.POLYGON_RPC_URL,
            'arbitrum': self.ARBITRUM_RPC_URL
        }
        return chain_urls.get(chain.lower(), self.ETHEREUM_RPC_URL)

# Global config instance
config = Config()