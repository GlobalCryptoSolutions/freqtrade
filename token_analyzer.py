import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Tuple
from web3 import Web3
from dataclasses import dataclass
from logger import logger
from config import config
from dex_monitor import NewPairEvent

@dataclass
class TokenAnalysis:
    """Data class for token analysis results"""
    token_address: str
    name: str
    symbol: str
    decimals: int
    total_supply: int
    liquidity_eth: float
    liquidity_usd: float
    market_cap: float
    buy_tax: float
    sell_tax: float
    is_honeypot: bool
    is_verified: bool
    owner_percentage: float
    locked_percentage: float
    risk_score: float  # 0-100, lower is better
    analysis_timestamp: int
    warnings: List[str]
    pair_address: str

class TokenAnalyzer:
    """Analyze tokens for safety and potential"""
    
    def __init__(self, chain: str = 'ethereum'):
        self.chain = chain
        self.w3 = Web3(Web3.HTTPProvider(config.get_rpc_url(chain)))
        
        # Known safe tokens (WETH, USDC, USDT, etc.)
        self.safe_tokens = {
            'ethereum': {
                '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
                '0xA0b86a33E6441e66e0c20D50bf24Ac0Dd18Bbfc3',  # USDC
                '0xdAC17F958D2ee523a2206206994597C13D831ec7',  # USDT
                '0x6B175474E89094C44Da98b954EedeAC495271d0F',  # DAI
            },
            'bsc': {
                '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',  # WBNB
                '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d',  # USDC
                '0x55d398326f99059fF775485246999027B3197955',  # USDT
            }
        }
        
        # Contract ABI for token analysis
        self.token_abi = config.ERC20_ABI + [
            {
                "constant": True,
                "inputs": [],
                "name": "owner",
                "outputs": [{"name": "", "type": "address"}],
                "type": "function"
            }
        ]
        
        logger.info(f"Token Analyzer initialized for {chain}")
    
    async def analyze_token(self, pair_event: NewPairEvent) -> Optional[TokenAnalysis]:
        """Analyze a token from a new pair event"""
        try:
            # Determine which token is the new one (not ETH/BNB/stable)
            token_address = self._identify_new_token(pair_event.token0, pair_event.token1)
            if not token_address:
                logger.warning(f"Could not identify new token in pair {pair_event.pair_address}")
                return None
            
            logger.info(f"Analyzing token: {token_address}")
            
            # Get basic token information
            token_info = await self._get_token_info(token_address)
            if not token_info:
                logger.error(f"Failed to get token info for {token_address}")
                return None
            
            # Get liquidity information
            liquidity_info = await self._get_liquidity_info(pair_event.pair_address, token_address)
            
            # Check for honeypot
            honeypot_check = await self._check_honeypot(token_address, pair_event.pair_address)
            
            # Get ownership and lock information
            ownership_info = await self._get_ownership_info(token_address)
            
            # Calculate risk score
            risk_score, warnings = self._calculate_risk_score(
                token_info, liquidity_info, honeypot_check, ownership_info
            )
            
            analysis = TokenAnalysis(
                token_address=token_address,
                name=token_info['name'],
                symbol=token_info['symbol'],
                decimals=token_info['decimals'],
                total_supply=token_info['total_supply'],
                liquidity_eth=liquidity_info['eth_amount'],
                liquidity_usd=liquidity_info['usd_value'],
                market_cap=liquidity_info['market_cap'],
                buy_tax=honeypot_check['buy_tax'],
                sell_tax=honeypot_check['sell_tax'],
                is_honeypot=honeypot_check['is_honeypot'],
                is_verified=await self._is_contract_verified(token_address),
                owner_percentage=ownership_info['owner_percentage'],
                locked_percentage=ownership_info['locked_percentage'],
                risk_score=risk_score,
                analysis_timestamp=int(time.time()),
                warnings=warnings,
                pair_address=pair_event.pair_address
            )
            
            logger.info(f"Token analysis complete. Risk Score: {risk_score}/100")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing token {token_address}: {e}")
            return None
    
    def _identify_new_token(self, token0: str, token1: str) -> Optional[str]:
        """Identify which token is the new one (not a known safe token)"""
        safe_tokens = self.safe_tokens.get(self.chain, set())
        
        if token0.lower() in [t.lower() for t in safe_tokens]:
            return token1
        elif token1.lower() in [t.lower() for t in safe_tokens]:
            return token0
        else:
            # Both tokens are unknown, return the second one by default
            # In practice, you might want more sophisticated logic here
            return token1
    
    async def _get_token_info(self, token_address: str) -> Optional[Dict]:
        """Get basic token information"""
        try:
            contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(token_address),
                abi=self.token_abi
            )
            
            # Get token details
            name = contract.functions.name().call()
            symbol = contract.functions.symbol().call()
            decimals = contract.functions.decimals().call()
            total_supply = contract.functions.totalSupply().call()
            
            return {
                'name': name,
                'symbol': symbol,
                'decimals': decimals,
                'total_supply': total_supply
            }
            
        except Exception as e:
            logger.error(f"Error getting token info for {token_address}: {e}")
            return None
    
    async def _get_liquidity_info(self, pair_address: str, token_address: str) -> Dict:
        """Get liquidity information for the token pair"""
        try:
            pair_contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(pair_address),
                abi=config.UNISWAP_V2_PAIR_ABI
            )
            
            # Get reserves
            reserves = pair_contract.functions.getReserves().call()
            token0_address = pair_contract.functions.token0().call()
            token1_address = pair_contract.functions.token1().call()
            
            # Determine which reserve corresponds to ETH/BNB
            if token0_address.lower() == token_address.lower():
                token_reserve = reserves[0]
                eth_reserve = reserves[1]
            else:
                token_reserve = reserves[1]
                eth_reserve = reserves[0]
            
            # Convert to human readable amounts
            eth_amount = eth_reserve / 10**18
            
            # Estimate USD value (simplified, you might want to use a price oracle)
            eth_price_usd = await self._get_eth_price()
            usd_value = eth_amount * eth_price_usd
            
            # Estimate market cap (simplified calculation)
            token_info = await self._get_token_info(token_address)
            if token_info and token_reserve > 0:
                token_price_eth = eth_reserve / token_reserve
                market_cap = (token_info['total_supply'] / 10**token_info['decimals']) * token_price_eth * eth_price_usd
            else:
                market_cap = 0
            
            return {
                'eth_amount': eth_amount,
                'usd_value': usd_value,
                'market_cap': market_cap,
                'token_reserve': token_reserve,
                'eth_reserve': eth_reserve
            }
            
        except Exception as e:
            logger.error(f"Error getting liquidity info for {pair_address}: {e}")
            return {
                'eth_amount': 0,
                'usd_value': 0,
                'market_cap': 0,
                'token_reserve': 0,
                'eth_reserve': 0
            }
    
    async def _get_eth_price(self) -> float:
        """Get current ETH price in USD"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd') as response:
                    data = await response.json()
                    return data['ethereum']['usd']
        except:
            # Fallback price if API fails
            return 3000.0
    
    async def _check_honeypot(self, token_address: str, pair_address: str) -> Dict:
        """Check if token is a honeypot using simulation"""
        try:
            # This is a simplified honeypot check
            # In practice, you would simulate buy/sell transactions
            
            # Try to simulate a small buy/sell to detect honeypots
            # For now, we'll use a basic heuristic approach
            
            result = {
                'is_honeypot': False,
                'buy_tax': 0.0,
                'sell_tax': 0.0,
                'can_sell_after_buy': True
            }
            
            # TODO: Implement actual honeypot detection via transaction simulation
            # This would involve:
            # 1. Simulating a small buy transaction
            # 2. Simulating a sell transaction
            # 3. Comparing expected vs actual amounts
            # 4. Checking for various honeypot patterns
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking honeypot for {token_address}: {e}")
            return {
                'is_honeypot': True,  # Assume honeypot if we can't verify
                'buy_tax': 0.0,
                'sell_tax': 0.0,
                'can_sell_after_buy': False
            }
    
    async def _get_ownership_info(self, token_address: str) -> Dict:
        """Get token ownership and lock information"""
        try:
            contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(token_address),
                abi=self.token_abi
            )
            
            total_supply = contract.functions.totalSupply().call()
            
            # Try to get owner
            owner_percentage = 0.0
            try:
                owner = contract.functions.owner().call()
                if owner and owner != '0x0000000000000000000000000000000000000000':
                    owner_balance = contract.functions.balanceOf(owner).call()
                    owner_percentage = (owner_balance / total_supply) * 100
            except:
                pass
            
            # TODO: Check for locked liquidity
            # This would involve checking common locker contracts
            locked_percentage = 0.0
            
            return {
                'owner_percentage': owner_percentage,
                'locked_percentage': locked_percentage
            }
            
        except Exception as e:
            logger.error(f"Error getting ownership info for {token_address}: {e}")
            return {
                'owner_percentage': 100.0,  # Assume worst case
                'locked_percentage': 0.0
            }
    
    async def _is_contract_verified(self, token_address: str) -> bool:
        """Check if contract is verified on Etherscan/BSCscan"""
        try:
            # This is a simplified check
            # In practice, you would query the block explorer API
            return False  # Default to unverified for safety
            
        except Exception as e:
            logger.error(f"Error checking verification for {token_address}: {e}")
            return False
    
    def _calculate_risk_score(self, token_info: Dict, liquidity_info: Dict, 
                             honeypot_check: Dict, ownership_info: Dict) -> Tuple[float, List[str]]:
        """Calculate risk score and generate warnings"""
        score = 0.0
        warnings = []
        
        # Liquidity checks
        if liquidity_info['eth_amount'] < config.MIN_LIQUIDITY_ETH:
            score += 30
            warnings.append(f"Low liquidity: {liquidity_info['eth_amount']:.3f} ETH")
        
        # Honeypot checks
        if honeypot_check['is_honeypot']:
            score += 50
            warnings.append("Detected as honeypot")
        
        if honeypot_check['buy_tax'] > config.MAX_BUY_TAX:
            score += 20
            warnings.append(f"High buy tax: {honeypot_check['buy_tax']:.1f}%")
        
        if honeypot_check['sell_tax'] > config.MAX_SELL_TAX:
            score += 20
            warnings.append(f"High sell tax: {honeypot_check['sell_tax']:.1f}%")
        
        # Ownership checks
        if ownership_info['owner_percentage'] > 50:
            score += 25
            warnings.append(f"High owner percentage: {ownership_info['owner_percentage']:.1f}%")
        
        if ownership_info['locked_percentage'] < 50:
            score += 15
            warnings.append(f"Low locked percentage: {ownership_info['locked_percentage']:.1f}%")
        
        # Token info checks
        if token_info['total_supply'] < 1000:
            score += 10
            warnings.append("Very low total supply")
        
        if len(token_info['name']) < 2 or len(token_info['symbol']) < 2:
            score += 10
            warnings.append("Suspicious token name/symbol")
        
        # Cap score at 100
        score = min(score, 100.0)
        
        return score, warnings
    
    def is_token_safe(self, analysis: TokenAnalysis) -> bool:
        """Determine if a token is safe to trade based on analysis"""
        if analysis.is_honeypot:
            return False
        
        if analysis.risk_score > 70:
            return False
        
        if analysis.liquidity_eth < config.MIN_LIQUIDITY_ETH:
            return False
        
        if analysis.buy_tax > config.MAX_BUY_TAX or analysis.sell_tax > config.MAX_SELL_TAX:
            return False
        
        return True

# Example usage
async def analyze_new_pair(pair_event: NewPairEvent):
    """Example function to analyze a new pair"""
    analyzer = TokenAnalyzer(pair_event.chain)
    analysis = await analyzer.analyze_token(pair_event)
    
    if analysis:
        logger.info(f"📊 TOKEN ANALYSIS COMPLETE")
        logger.info(f"   Token: {analysis.symbol} ({analysis.name})")
        logger.info(f"   Liquidity: {analysis.liquidity_eth:.3f} ETH (${analysis.liquidity_usd:.0f})")
        logger.info(f"   Risk Score: {analysis.risk_score}/100")
        logger.info(f"   Is Safe: {analyzer.is_token_safe(analysis)}")
        
        if analysis.warnings:
            logger.warning(f"   Warnings: {', '.join(analysis.warnings)}")
    
    return analysis

if __name__ == "__main__":
    # Test the analyzer
    async def test_analyzer():
        # Create a sample pair event for testing
        from dex_monitor import NewPairEvent
        
        test_event = NewPairEvent(
            token0='0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
            token1='0x1234567890123456789012345678901234567890',  # Sample token
            pair_address='0x1234567890123456789012345678901234567890',
            block_number=12345678,
            transaction_hash='0x1234567890123456789012345678901234567890123456789012345678901234',
            timestamp=int(time.time()),
            dex='uniswap_v2',
            chain='ethereum'
        )
        
        analysis = await analyze_new_pair(test_event)
        return analysis
    
    asyncio.run(test_analyzer())