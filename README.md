# OSRS Flipping Tool

A Python tool that analyzes the Old School RuneScape Grand Exchange (GE) to find profitable flipping opportunities. The tool uses the official OSRS GE API to gather real-time price data and historical trends.

## Features

- **Real-time Price Analysis**: Uses the latest GE prices and 24-hour averages to identify profitable opportunities
- **Smart Filtering**:
  - Minimum volume requirements to ensure items are actively traded
  - Minimum margin percentage to ensure profitable trades
  - GE tax consideration (1% for items over 100gp)
  - Bond conversion cost consideration (10% for bonds)
  - Price consistency checks against 7-day historical data
  - Buy limit and reset time consideration
  - Capital requirement filtering based on available cash

- **Comprehensive Scoring System**:
  - Considers profit per trade
  - Accounts for buy limits and reset times
  - Factors in trading volume
  - Penalizes items with low volume relative to buy limits
  - Rewards items with high profit margins
  - Normalizes scores to 0-100 scale

- **Detailed Output**:
  - Sorts opportunities by profit potential
  - Shows required capital and expected returns
  - Displays buy limits and reset times
  - Provides volume information for both buying and selling
  - Categorizes opportunities by profit range:
    - 0-100k profit per trade
    - 100k-500k profit per trade
    - 500k-1m profit per trade
    - 1m+ profit per trade

## Requirements

- Python 3.6+
- Required packages:
  ```
  requests
  pandas
  ```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/OSRSFlippingTool.git
   cd OSRSFlippingTool
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the script:
```bash
python osrs_flipper.py
```

The script will:
1. Prompt for your available cash (in millions)
2. Analyze current GE prices and historical data
3. Generate separate files for different profit ranges
4. Display the top 20 opportunities in the console

## Output Files

The script generates four separate files based on profit ranges:
- `flipping_opportunities_0-100k.txt`: Items with 0-100k profit per trade
- `flipping_opportunities_100k-500k.txt`: Items with 100k-500k profit per trade
- `flipping_opportunities_500k-1m.txt`: Items with 500k-1m profit per trade
- `flipping_opportunities_1m+.txt`: Items with 1m+ profit per trade

Each file contains detailed information about each opportunity, sorted by profit per trade in ascending order.

## API Usage

The tool uses the official OSRS GE API endpoints:
- `/mapping`: For item names, buy limits, and reset times
- `/latest`: For current GE prices
- `/24h`: For 24-hour price averages and volumes
- `/timeseries`: For 7-day price history (used for top 20 opportunities)

## Contributing

Feel free to submit issues and enhancement requests! 