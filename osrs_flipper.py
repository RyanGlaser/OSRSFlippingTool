import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import time
from typing import Dict, List, Tuple

class OSRSFlipper:
    def __init__(self):
        self.base_url = "https://prices.runescape.wiki/api/v1/osrs"
        self.headers = {
            "User-Agent": "OSRSFlipper/1.0 (https://github.com/yourusername/OSRSFlippingTool; ryanglaser150@gmail.com)"
        }
        self.item_names = self._load_item_names()

    def _load_item_names(self) -> Dict[str, Dict]:
        """Load item names, buy limits, and reset times from the OSRS API."""
        try:
            response = requests.get(f"{self.base_url}/mapping", headers=self.headers)
            response.raise_for_status()
            items = response.json()
            print(f"\nLoaded {len(items)} item names from mapping API")
            
            # Print sample of first item to see structure
            if items:
                print("\nSample item structure:")
                print(json.dumps(items[0], indent=2))
            
            # Store name, buy limit, and reset time for each item
            item_dict = {}
            for item in items:
                reset_time = item.get('reset_time', 14400)  # Default to 4 hours (14400 seconds) if not specified
                item_dict[str(item['id'])] = {
                    'name': item['name'], 
                    'buy_limit': item.get('limit'),
                    'reset_time': reset_time
                }
                
                # Print items with non-standard reset times
                if reset_time != 14400:
                    print(f"\nFound item with non-standard reset time:")
                    print(f"Item: {item['name']}")
                    print(f"Reset Time: {reset_time/3600:.1f} hours")
                    print(f"Buy Limit: {item.get('limit')}")
            
            return item_dict
        except requests.RequestException as e:
            print(f"Error loading item names: {e}")
            return {}

    def _calculate_ge_tax(self, sell_price: int) -> int:
        """Calculate the GE tax for a given sell price."""
        if sell_price <= 100:
            return 0
        return int(sell_price * 0.01)  # 1% tax

    def _calculate_bond_conversion_cost(self, price: int) -> int:
        """Calculate the cost to convert a bond to tradeable form."""
        return int(price * 0.10)  # 10% conversion cost

    def _calculate_opportunity_score(self, margin_percentage: float, high_volume: int, low_volume: int, price: int, buy_limit: int, reset_time: int) -> float:
        """Calculate a score for the opportunity based on margin, volume, and practical considerations."""
        # Calculate profit per trade
        profit_per_trade = price * (margin_percentage / 100)
        
        # Skip items with very low profit per trade (less than 100gp)
        if profit_per_trade < 100:
            return 0
            
        # Calculate how many periods we can complete in 24 hours
        periods_per_day = 86400 / reset_time  # 86400 seconds in a day
        
        # Calculate volumes per period
        high_volume_per_period = high_volume / periods_per_day
        low_volume_per_period = low_volume / periods_per_day
        
        # Calculate total potential profit per day
        potential_profit_per_day = profit_per_trade * buy_limit * periods_per_day
        
        # Calculate tradeability factor based on both high and low price volumes
        # We need both high volume (to sell) and low volume (to buy) for successful flipping
        min_volume = min(high_volume, low_volume)
        max_possible_trades_per_day = buy_limit * periods_per_day
        
        # If either volume is too low, reduce the score significantly
        if min_volume < max_possible_trades_per_day:
            volume_factor = min_volume / max_possible_trades_per_day
            # Apply a penalty for low volume, but less severe
            volume_factor = volume_factor ** 1.5  # Changed from square to 1.5 power
            potential_profit_per_day *= volume_factor
        
        # Add a penalty if low volume per period is less than buy limit
        if low_volume_per_period < buy_limit:
            # Calculate how much of the buy limit we can actually buy
            buy_limit_factor = low_volume_per_period / buy_limit
            # Apply a penalty for not being able to buy the full limit, but less severe
            potential_profit_per_day *= (buy_limit_factor ** 1.5)  # Changed from cube to 1.5 power
        
        # Add a multiplier for high profit per trade items, with stronger emphasis
        profit_multiplier = 1.0
        if profit_per_trade > 1_000_000:  # 1M+ profit per trade
            profit_multiplier = 2.0  # Increased from 1.5
        elif profit_per_trade > 500_000:  # 500k+ profit per trade
            profit_multiplier = 1.7  # Increased from 1.3
        elif profit_per_trade > 100_000:  # 100k+ profit per trade
            profit_multiplier = 1.4  # Increased from 1.1
        
        # Add a small bonus for items with higher buy limits, but less impactful
        buy_limit_multiplier = 1.0 + (buy_limit / 5000)  # Reduced from 2000 to 5000 to make it less impactful
        
        # Add a bonus for items with good volume relative to buy limit
        volume_ratio = min(high_volume_per_period, low_volume_per_period) / buy_limit
        volume_multiplier = 1.0 + min(volume_ratio, 2.0)  # Max 3x bonus for very high volume
        
        return potential_profit_per_day * profit_multiplier * buy_limit_multiplier * volume_multiplier

    def get_latest_prices(self) -> Dict:
        """Fetch the latest prices from the OSRS GE API."""
        try:
            response = requests.get(f"{self.base_url}/latest", headers=self.headers)
            response.raise_for_status()
            data = response.json()
            print(f"\nLatest prices API response:")
            print(f"Total items: {len(data['data'])}")
            print(f"Sample of first 3 items:")
            for item_id, item_data in list(data['data'].items())[:3]:
                print(f"Item ID: {item_id}")
                print(f"High: {item_data.get('high', 'N/A')}")
                print(f"Low: {item_data.get('low', 'N/A')}")
            return data['data']
        except requests.RequestException as e:
            print(f"Error fetching latest prices: {e}")
            return {}

    def get_24h_prices(self) -> Dict:
        """Fetch 24-hour price history from the OSRS GE API."""
        try:
            response = requests.get(f"{self.base_url}/24h", headers=self.headers)
            response.raise_for_status()
            data = response.json()
            print(f"\n24h prices API response:")
            print(f"Total items: {len(data['data'])}")
            print(f"Sample of first 3 items:")
            for item_id, item_data in list(data['data'].items())[:3]:
                print(f"Item ID: {item_id}")
                print(f"Avg High: {item_data.get('avgHighPrice', 'N/A')}")
                print(f"Avg Low: {item_data.get('avgLowPrice', 'N/A')}")
                print(f"Volume: {item_data.get('highPriceVolume', 'N/A')}")
            return data['data']
        except requests.RequestException as e:
            print(f"Error fetching 24h prices: {e}")
            return {}

    def get_7d_prices(self, item_ids: List[str]) -> Dict[str, Dict]:
        """Fetch 7-day price history for multiple items from the OSRS GE API."""
        results = {}
        
        for item_id in item_ids:
            try:
                response = requests.get(
                    f"{self.base_url}/timeseries",
                    params={
                        "id": item_id,
                        "timestep": "24h"  # 24-hour intervals
                    },
                    headers=self.headers
                )
                response.raise_for_status()
                data = response.json()
                
                if not data.get('data'):
                    continue
                    
                item_data = data['data']
                if not item_data:
                    continue
                    
                # Get all high and low prices
                high_prices = [p.get('avgHighPrice', 0) for p in item_data if p.get('avgHighPrice')]
                low_prices = [p.get('avgLowPrice', 0) for p in item_data if p.get('avgLowPrice')]
                
                if not high_prices or not low_prices:
                    continue
                
                # Sort prices to calculate percentiles
                high_prices.sort()
                low_prices.sort()
                
                # Calculate 5th and 95th percentiles
                high_5th = high_prices[int(len(high_prices) * 0.05)]
                high_95th = high_prices[int(len(high_prices) * 0.95)]
                low_5th = low_prices[int(len(low_prices) * 0.05)]
                low_95th = low_prices[int(len(low_prices) * 0.95)]
                
                # Calculate average of 5th percentile range (bottom 5% of prices)
                avg_low_5th = sum(low_prices[:int(len(low_prices) * 0.05)]) / int(len(low_prices) * 0.05)
                avg_high_5th = sum(high_prices[:int(len(high_prices) * 0.05)]) / int(len(high_prices) * 0.05)
                
                # Calculate average of 95th percentile range (top 5% of prices)
                avg_low_95th = sum(low_prices[int(len(low_prices) * 0.95):]) / (len(low_prices) - int(len(low_prices) * 0.95))
                avg_high_95th = sum(high_prices[int(len(high_prices) * 0.95):]) / (len(high_prices) - int(len(high_prices) * 0.95))
                
                # Calculate average of middle 90% range
                avg_high = sum(high_prices[int(len(high_prices) * 0.05):int(len(high_prices) * 0.95)]) / (len(high_prices) * 0.9)
                avg_low = sum(low_prices[int(len(low_prices) * 0.05):int(len(low_prices) * 0.95)]) / (len(low_prices) * 0.9)
                
                # Calculate standard deviation of the middle 90% range
                high_std = (sum((x - avg_high) ** 2 for x in high_prices[int(len(high_prices) * 0.05):int(len(high_prices) * 0.95)]) / (len(high_prices) * 0.9)) ** 0.5
                low_std = (sum((x - avg_low) ** 2 for x in low_prices[int(len(low_prices) * 0.05):int(len(low_prices) * 0.95)]) / (len(low_prices) * 0.9)) ** 0.5
                
                # Calculate average volumes
                high_volumes = [p.get('highPriceVolume', 0) for p in item_data if p.get('highPriceVolume')]
                low_volumes = [p.get('lowPriceVolume', 0) for p in item_data if p.get('lowPriceVolume')]
                
                avg_high_volume = sum(high_volumes) / len(high_volumes) if high_volumes else 0
                avg_low_volume = sum(low_volumes) / len(low_volumes) if low_volumes else 0
                
                results[item_id] = {
                    'avg_high': avg_high,
                    'avg_low': avg_low,
                    'high_std': high_std,
                    'low_std': low_std,
                    'high_5th': high_5th,
                    'high_95th': high_95th,
                    'low_5th': low_5th,
                    'low_95th': low_95th,
                    'avg_high_5th': avg_high_5th,  # Average of bottom 5% of high prices
                    'avg_low_5th': avg_low_5th,    # Average of bottom 5% of low prices
                    'avg_high_95th': avg_high_95th,  # Average of top 5% of high prices
                    'avg_low_95th': avg_low_95th,    # Average of top 5% of low prices
                    'avg_high_volume': avg_high_volume,
                    'avg_low_volume': avg_low_volume,
                    'data_points': len(item_data)
                }
                
            except requests.RequestException as e:
                print(f"Error fetching 7d prices for item {item_id}: {e}")
                continue
        
        return results

    def _is_price_consistent(self, current_high: int, current_low: int, historical_data: Dict) -> bool:
        """Check if current prices are consistent with historical data."""
        if not historical_data:
            return False
            
        # Check if current prices are within 2 standard deviations of historical averages
        high_within_range = abs(current_high - historical_data['avg_high']) <= (2 * historical_data['high_std'])
        low_within_range = abs(current_low - historical_data['avg_low']) <= (2 * historical_data['low_std'])
        
        # Check if current prices are within the 5th-95th percentile range
        high_within_percentile = historical_data['high_5th'] <= current_high <= historical_data['high_95th']
        low_within_percentile = historical_data['low_5th'] <= current_low <= historical_data['low_95th']
        
        return high_within_range and low_within_range and high_within_percentile and low_within_percentile

    def _calculate_required_capital(self, buy_price: int, buy_limit: int, ge_tax: int, bond_conversion_cost: int) -> int:
        """Calculate the total capital required to flip an item."""
        # Cost to buy the items
        buy_cost = buy_price * buy_limit
        
        # Add GE tax and bond conversion cost, if item is not a bond then bond_conversion_cost is 0
        total_cost = buy_cost + ge_tax + bond_conversion_cost
        
        # Add a 5% buffer for price fluctuations
        return int(total_cost * 1.05)

    def _calculate_expected_capital_after_flip(self, required_capital: int, margin: int, buy_limit: int, low_volume_per_period: float) -> int:
        """Calculate the expected capital after flipping, taking into account achievable volume."""
        # Calculate how many items we can actually buy based on volume
        achievable_items = min(buy_limit, int(low_volume_per_period))
        
        # Calculate profit from achievable items
        profit = margin * achievable_items
        
        # Return initial capital plus profit
        return required_capital + profit

    def analyze_flipping_opportunities(self, min_volume: int = 100, min_margin: float = 0.5, available_cash: int = None) -> List[Dict]:
        """Analyze items for flipping opportunities."""
        latest_prices = self.get_latest_prices()
        daily_prices = self.get_24h_prices()
        
        print(f"\nAnalysis starting with:")
        print(f"Latest prices: {len(latest_prices)} items")
        print(f"24h prices: {len(daily_prices)} items")
        if available_cash:
            print(f"Available cash: {available_cash:,} gp")
        
        opportunities = []
        skipped_items = 0
        low_volume_items = 0
        low_margin_items = 0
        unrealistic_price_items = 0
        low_profit_items = 0
        missing_buy_limit_items = 0
        insufficient_cash_items = 0
        inconsistent_price_items = 0
        
        # First pass: collect all opportunities
        for item_id, data in latest_prices.items():
            if item_id not in daily_prices:
                skipped_items += 1
                continue
                
            daily_data = daily_prices[item_id]
            current_high = data.get('high', 0)
            current_low = data.get('low', 0)
            
            # Skip items with missing or invalid prices
            if current_high is None or current_low is None or current_high <= 0 or current_low <= 0:
                skipped_items += 1
                continue
            
            # Skip items with unrealistic price spreads
            current_spread = (current_high - current_low) / current_low
            if current_spread > 0.5:  # Skip if current spread is >50%
                unrealistic_price_items += 1
                continue
            
            # Get the average high and low prices from the 24h data
            daily_high = daily_data.get('avgHighPrice', 0)
            daily_low = daily_data.get('avgLowPrice', 0)
            high_volume = daily_data.get('highPriceVolume', 0)
            low_volume = daily_data.get('lowPriceVolume', 0)
            
            # Skip items with missing or invalid 24h data
            if daily_high is None or daily_low is None or daily_high <= 0 or daily_low <= 0:
                skipped_items += 1
                continue
            
            # Check both high and low volumes
            if high_volume is None or low_volume is None or high_volume < min_volume or low_volume < min_volume:
                low_volume_items += 1
                continue
            
            # Calculate potential profit margin using current prices    
            # Include GE tax in calculations
            ge_tax = self._calculate_ge_tax(current_high)
            
            # Check if this is a bond (item_id for bonds is "13190")
            is_bond = item_id == "13190"
            bond_conversion_cost = self._calculate_bond_conversion_cost(current_high) if is_bond else 0
            
            margin = current_high - current_low - ge_tax - bond_conversion_cost
            margin_percentage = (margin / current_low) * 100
            
            if margin_percentage < min_margin:
                low_margin_items += 1
                continue
            
            # Get item name, buy limit, and reset time
            item_info = self.item_names.get(item_id, {'name': 'Unknown', 'buy_limit': None, 'reset_time': 14400})
            item_name = item_info['name']
            buy_limit = item_info['buy_limit']
            reset_time = item_info['reset_time']
            
            # Skip items with missing buy limit
            if buy_limit is None:
                missing_buy_limit_items += 1
                continue
            
            # Calculate required capital
            required_capital = self._calculate_required_capital(current_low, buy_limit, ge_tax, bond_conversion_cost)
            
            # Skip items that require more capital than available
            if available_cash and required_capital > available_cash:
                insufficient_cash_items += 1
                continue
            
            # Calculate volumes per period
            periods_per_day = 86400 / reset_time
            high_volume_per_period = high_volume / periods_per_day
            low_volume_per_period = low_volume / periods_per_day
            
            # Calculate achievable profit per buy window based on actual volume
            achievable_items = min(buy_limit, int(low_volume_per_period))
            achievable_profit = margin * achievable_items
            
            # Calculate expected capital after flip
            expected_capital = self._calculate_expected_capital_after_flip(required_capital, margin, buy_limit, low_volume_per_period)
            
            # Calculate opportunity score
            score = self._calculate_opportunity_score(margin_percentage, high_volume, low_volume, current_high, buy_limit, reset_time)
            
            # Skip items with zero score (low profit per trade)
            if score == 0:
                low_profit_items += 1
                continue
            
            opportunities.append({
                'item_id': item_id,
                'name': item_name,
                'buy_limit': buy_limit,
                'reset_time': reset_time,
                'buy_price': current_low,
                'sell_price': current_high,
                'ge_tax': ge_tax,
                'bond_conversion_cost': bond_conversion_cost,
                'daily_avg_high': daily_high,
                'daily_avg_low': daily_low,
                'high_volume': high_volume,
                'low_volume': low_volume,
                'margin': margin,
                'margin_percentage': margin_percentage,
                'profit_per_window': achievable_profit,
                'achievable_items': achievable_items,
                'required_capital': required_capital,
                'expected_capital': expected_capital,
                'raw_score': score
            })
        
        # Sort by raw score to get top opportunities
        opportunities.sort(key=lambda x: x['raw_score'], reverse=True)
        
        # Get 7-day price history only for top 20 opportunities
        print("\nFetching 7-day price history for top 20 opportunities...")
        top_opportunities = opportunities[:20]
        item_ids = [opp['item_id'] for opp in top_opportunities]
        historical_data = self.get_7d_prices(item_ids)
        
        # Filter opportunities based on price consistency
        filtered_opportunities = []
        filtered_count = 0
        
        for opp in top_opportunities:
            historical = historical_data.get(opp['item_id'])
            if not self._is_price_consistent(opp['sell_price'], opp['buy_price'], historical):
                inconsistent_price_items += 1
                filtered_count += 1
                continue
                
            # Add historical data to the opportunity
            opp['weekly_avg_high'] = historical['avg_high']
            opp['weekly_avg_low'] = historical['avg_low']
            
            # Print debug info for items with significant margins
            print(f"\nFound potential opportunity:")
            print(f"Item: {opp['name']}")
            print(f"Buy Limit: {opp['buy_limit']:,} per {opp['reset_time']/3600:.1f}h")
            print(f"Current Low (Buy): {opp['buy_price']:,} gp")
            print(f"Current High (Sell): {opp['sell_price']:,} gp")
            print(f"GE Tax: {opp['ge_tax']:,} gp")
            if opp['bond_conversion_cost'] > 0:
                print(f"Bond Conversion Cost: {opp['bond_conversion_cost']:,} gp")
            print(f"24h Avg High: {opp['daily_avg_high']:,} gp")
            print(f"24h Avg Low: {opp['daily_avg_low']:,} gp")
            print(f"7d Avg High: {historical['avg_high']:,.0f} gp")
            print(f"7d Avg Low: {historical['avg_low']:,.0f} gp")
            print(f"Margin (after tax): {opp['margin_percentage']:.2f}%")
            print(f"High Price Volume: {opp['high_volume']:,}")
            print(f"Low Price Volume: {opp['low_volume']:,}")
            print(f"Profit per trade: {opp['margin']:,} gp")
            print(f"Profit per buy window: {opp['profit_per_window']:,} gp (achievable items: {opp['achievable_items']:,})")
            print(f"Required Capital: {opp['required_capital']:,} gp")
            print(f"Expected Capital After Flip: {opp['expected_capital']:,} gp")
            print(f"Raw Score: {opp['raw_score']:,.0f}")
            
            filtered_opportunities.append(opp)
        
        # If we filtered out any items, get replacements from outside the top 20
        if filtered_count > 0:
            print(f"\nFetching 7-day price history for {filtered_count} replacement opportunities...")
            replacement_opportunities = opportunities[20:20 + filtered_count]
            replacement_ids = [opp['item_id'] for opp in replacement_opportunities]
            replacement_data = self.get_7d_prices(replacement_ids)
            
            for opp in replacement_opportunities:
                historical = replacement_data.get(opp['item_id'])
                if not self._is_price_consistent(opp['sell_price'], opp['buy_price'], historical):
                    inconsistent_price_items += 1
                    continue
                    
                # Add historical data to the opportunity
                opp['weekly_avg_high'] = historical['avg_high']
                opp['weekly_avg_low'] = historical['avg_low']
                
                # Print debug info for replacement items
                print(f"\nFound replacement opportunity:")
                print(f"Item: {opp['name']}")
                print(f"Buy Limit: {opp['buy_limit']:,} per {opp['reset_time']/3600:.1f}h")
                print(f"Current Low (Buy): {opp['buy_price']:,} gp")
                print(f"Current High (Sell): {opp['sell_price']:,} gp")
                print(f"GE Tax: {opp['ge_tax']:,} gp")
                if opp['bond_conversion_cost'] > 0:
                    print(f"Bond Conversion Cost: {opp['bond_conversion_cost']:,} gp")
                print(f"24h Avg High: {opp['daily_avg_high']:,} gp")
                print(f"24h Avg Low: {opp['daily_avg_low']:,} gp")
                print(f"7d Avg High: {historical['avg_high']:,.0f} gp")
                print(f"7d Avg Low: {historical['avg_low']:,.0f} gp")
                print(f"Margin (after tax): {opp['margin_percentage']:.2f}%")
                print(f"High Price Volume: {opp['high_volume']:,}")
                print(f"Low Price Volume: {opp['low_volume']:,}")
                print(f"Profit per trade: {opp['margin']:,} gp")
                print(f"Profit per buy window: {opp['profit_per_window']:,} gp (achievable items: {opp['achievable_items']:,})")
                print(f"Required Capital: {opp['required_capital']:,} gp")
                print(f"Expected Capital After Flip: {opp['expected_capital']:,} gp")
                print(f"Raw Score: {opp['raw_score']:,.0f}")
                
                filtered_opportunities.append(opp)
            
            # If we still don't have 20 items, fetch more replacements
            while len(filtered_opportunities) < 20 and len(opportunities) > 20 + filtered_count:
                next_batch_start = 20 + filtered_count
                next_batch_end = min(next_batch_start + 5, len(opportunities))  # Fetch 5 at a time
                next_batch = opportunities[next_batch_start:next_batch_end]
                
                print(f"\nFetching 7-day price history for {len(next_batch)} additional replacement opportunities...")
                next_batch_ids = [opp['item_id'] for opp in next_batch]
                next_batch_data = self.get_7d_prices(next_batch_ids)
                
                for opp in next_batch:
                    historical = next_batch_data.get(opp['item_id'])
                    if not self._is_price_consistent(opp['sell_price'], opp['buy_price'], historical):
                        inconsistent_price_items += 1
                        continue
                        
                    # Add historical data to the opportunity
                    opp['weekly_avg_high'] = historical['avg_high']
                    opp['weekly_avg_low'] = historical['avg_low']
                    
                    # Print debug info for additional replacement items
                    print(f"\nFound additional replacement opportunity:")
                    print(f"Item: {opp['name']}")
                    print(f"Buy Limit: {opp['buy_limit']:,} per {opp['reset_time']/3600:.1f}h")
                    print(f"Current Low (Buy): {opp['buy_price']:,} gp")
                    print(f"Current High (Sell): {opp['sell_price']:,} gp")
                    print(f"GE Tax: {opp['ge_tax']:,} gp")
                    if opp['bond_conversion_cost'] > 0:
                        print(f"Bond Conversion Cost: {opp['bond_conversion_cost']:,} gp")
                    print(f"24h Avg High: {opp['daily_avg_high']:,} gp")
                    print(f"24h Avg Low: {opp['daily_avg_low']:,} gp")
                    print(f"7d Avg High: {historical['avg_high']:,.0f} gp")
                    print(f"7d Avg Low: {historical['avg_low']:,.0f} gp")
                    print(f"Margin (after tax): {opp['margin_percentage']:.2f}%")
                    print(f"High Price Volume: {opp['high_volume']:,}")
                    print(f"Low Price Volume: {opp['low_volume']:,}")
                    print(f"Profit per trade: {opp['margin']:,} gp")
                    print(f"Profit per buy window: {opp['profit_per_window']:,} gp (achievable items: {opp['achievable_items']:,})")
                    print(f"Required Capital: {opp['required_capital']:,} gp")
                    print(f"Expected Capital After Flip: {opp['expected_capital']:,} gp")
                    print(f"Raw Score: {opp['raw_score']:,.0f}")
                    
                    filtered_opportunities.append(opp)
                    
                    if len(filtered_opportunities) >= 20:
                        break
                
                filtered_count += len(next_batch)
        
        # Normalize scores to 0-100 scale
        if filtered_opportunities:
            max_score = max(opp['raw_score'] for opp in filtered_opportunities)
            for opp in filtered_opportunities:
                opp['score'] = (opp['raw_score'] / max_score) * 100
        
        print(f"\nAnalysis Summary:")
        print(f"Skipped {skipped_items} items due to missing or invalid data")
        print(f"Filtered out {low_volume_items} items due to low volume")
        print(f"Filtered out {low_margin_items} items due to low margin")
        print(f"Filtered out {unrealistic_price_items} items due to unrealistic price spreads")
        print(f"Filtered out {low_profit_items} items due to low profit per trade")
        print(f"Filtered out {missing_buy_limit_items} items due to missing buy limit")
        print(f"Filtered out {inconsistent_price_items} items due to inconsistent 7-day price history")
        if available_cash:
            print(f"Filtered out {insufficient_cash_items} items due to insufficient capital")
        print(f"Found {len(filtered_opportunities)} opportunities with >{min_margin}% margin (after tax)")
        
        return filtered_opportunities

    def save_opportunities(self, opportunities: List[Dict]):
        """Save flipping opportunities to separate files based on profit per trade ranges."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Define profit ranges
        profit_ranges = [
            (0, 100000, "0-100k"),
            (100000, 500000, "100k-500k"),
            (500000, 1000000, "500k-1m"),
            (1000000, float('inf'), "1m+")
        ]
        
        # Create a file for each profit range
        for min_profit, max_profit, range_name in profit_ranges:
            filename = f'flipping_opportunities_{range_name}.txt'
            with open(filename, 'w') as f:
                f.write(f"OSRS Flipping Opportunities ({range_name} profit per trade) - Generated at {timestamp}\n")
                f.write("=" * 50 + "\n\n")
                
                # Filter opportunities for this range
                range_opportunities = [opp for opp in opportunities 
                                    if min_profit <= opp['margin'] < max_profit]
                
                # Sort by profit per trade in ascending order
                range_opportunities.sort(key=lambda x: x['margin'])
                
                for opp in range_opportunities:
                    # Calculate volumes per buy period
                    periods_per_day = 86400 / opp['reset_time']
                    high_volume_per_period = opp['high_volume'] / periods_per_day
                    low_volume_per_period = opp['low_volume'] / periods_per_day
                    
                    f.write(f"Item: {opp['name']}\n")
                    f.write(f"Buy Limit: {opp['buy_limit']:,} per {opp['reset_time']/3600:.1f}h\n")
                    f.write(f"Buy Price: {opp['buy_price']:,} gp\n")
                    f.write(f"Current Sell Price: {opp['sell_price']:,} gp\n")
                    f.write(f"GE Tax: {opp['ge_tax']:,} gp\n")
                    if opp['bond_conversion_cost'] > 0:
                        f.write(f"Bond Conversion Cost: {opp['bond_conversion_cost']:,} gp\n")
                    f.write(f"24h Avg High: {opp['daily_avg_high']:,} gp\n")
                    f.write(f"24h Avg Low: {opp['daily_avg_low']:,} gp\n")
                    f.write(f"Potential Profit (after tax): {opp['margin']:,} gp ({opp['margin_percentage']:.2f}%)\n")
                    f.write(f"Profit per buy window: {opp['profit_per_window']:,} gp (achievable items: {opp['achievable_items']:,})\n")
                    f.write(f"Required Capital: {opp['required_capital']:,} gp\n")
                    f.write(f"Expected Capital After Flip: {opp['expected_capital']:,} gp\n")
                    f.write(f"24h High Price Volume: {opp['high_volume']:,}\n")
                    f.write(f"24h Low Price Volume: {opp['low_volume']:,}\n")
                    f.write(f"High Price Volume per {opp['reset_time']/3600:.1f}h: {high_volume_per_period:,.1f}\n")
                    f.write(f"Low Price Volume per {opp['reset_time']/3600:.1f}h: {low_volume_per_period:,.1f}\n")
                    f.write(f"Raw Score: {opp['raw_score']:,.0f}\n")
                    f.write(f"Normalized Score: {opp['score']:.1f}/100\n")
                    f.write("-" * 30 + "\n")
                
                print(f"Saved {len(range_opportunities)} opportunities with {range_name} profit per trade to {filename}")

def main():
    flipper = OSRSFlipper()
    print("Analyzing OSRS flipping opportunities...")
    
    # Get available cash from user
    while True:
        try:
            available_cash = input("\nEnter your available cash (in millions, e.g., 10 for 10M): ")
            if available_cash.lower() == 'q':
                return
            available_cash = int(float(available_cash) * 1_000_000)  # Convert millions to gp
            break
        except ValueError:
            print("Please enter a valid number (e.g., 10 for 10M)")
    
    opportunities = flipper.analyze_flipping_opportunities(min_volume=100, min_margin=0.5, available_cash=available_cash)
    
    if opportunities:
        flipper.save_opportunities(opportunities)
        print(f"\nFound {len(opportunities)} potential flipping opportunities!")
        
        # Print top 20 opportunities
        print("\nTop 20 Opportunities:")
        for i, opp in enumerate(opportunities[:20], 1):
            # Calculate volumes per buy period
            periods_per_day = 86400 / opp['reset_time']
            high_volume_per_period = opp['high_volume'] / periods_per_day
            low_volume_per_period = opp['low_volume'] / periods_per_day
            
            print(f"\n{i}. {opp['name']}")
            print(f"   Score: {opp['score']:.1f}/100")
            print(f"   Profit per trade: {opp['margin']:,} gp")
            print(f"   Profit per buy window: {opp['profit_per_window']:,} gp (achievable items: {opp['achievable_items']:,})")
            print(f"   Required Capital: {opp['required_capital']:,} gp")
            print(f"   Expected Capital After Flip: {opp['expected_capital']:,} gp")
            print(f"   Buy Limit: {opp['buy_limit']:,} per {opp['reset_time']/3600:.1f}h")
            print(f"   24h High Price Volume: {opp['high_volume']:,}")
            print(f"   24h Low Price Volume: {opp['low_volume']:,}")
            print(f"   High Price Volume per {opp['reset_time']/3600:.1f}h: {high_volume_per_period:,.1f}")
            print(f"   Low Price Volume per {opp['reset_time']/3600:.1f}h: {low_volume_per_period:,.1f}")
    else:
        print("\nNo good flipping opportunities found at this time.")

if __name__ == "__main__":
    main() 