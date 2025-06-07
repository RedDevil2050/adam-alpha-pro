<!-- filepath: d:\Zion\INDIAN_EQUITY_SYMBOLS.md -->
# Indian Equity Symbol Handling System

## Overview

The Zion trading system now supports comprehensive handling of Indian equity symbols from NSE, BSE, and major indices. The system automatically normalizes symbols for different data providers and validates symbol formats.

## Supported Symbol Formats

### NSE Symbols

- **Raw format**: `RELIANCE`, `TCS`, `HDFCBANK`
- **Yahoo Finance format**: `RELIANCE.NS`, `TCS.NS`, `HDFCBANK.NS`
- **Auto-detection**: Raw Indian symbols are automatically detected and normalized

### BSE Symbols

- **Raw format**: `RELIANCE`, `TCS`, `HDFCBANK`
- **Yahoo Finance format**: `RELIANCE.BO`, `TCS.BO`, `HDFCBANK.BO`
- **Numerical codes**: `500325`, `532540` (6-digit BSE codes)

### Index Symbols

- **By name**: `NIFTY`, `SENSEX`, `BANKNIFTY`
- **Yahoo format**: `^NSEI`, `^BSESN`, `^NSEBANK`
- **Auto-mapping**: Index names are automatically mapped to correct formats

## Key Features

### 1. Automatic Symbol Normalization

```python
from backend.utils.symbol_normalizer import normalize_indian_symbol

# Normalize for different providers
yahoo_symbol = normalize_indian_symbol("RELIANCE", "yahoo")        # Returns: "RELIANCE.NS"
alpha_symbol = normalize_indian_symbol("RELIANCE.NS", "alpha_vantage")  # Returns: "RELIANCE"
polygon_symbol = normalize_indian_symbol("TCS", "polygon")         # Returns: "TCS"
```

### 2. Symbol Validation

```python
from backend.utils.symbol_normalizer import validate_indian_symbol

is_valid, error_msg = validate_indian_symbol("RELIANCE")  # Returns: (True, "")
is_valid, error_msg = validate_indian_symbol("INVALID@")  # Returns: (False, "Invalid characters...")
```

### 3. Enhanced Request Validation

```python
from backend.security.validate import SymbolRequest, EnhancedSymbolRequest

# Basic validation
request = SymbolRequest(symbol="RELIANCE")

# Enhanced validation with provider-specific normalization
enhanced = EnhancedSymbolRequest(symbol="TCS", provider="yahoo")
print(enhanced.normalized_symbol)  # "TCS.NS"
```

### 4. Unified Data Provider Integration

```python
from backend.data.providers.unified_provider import UnifiedDataProvider

provider = UnifiedDataProvider()

# Fetch data - symbols are automatically normalized for each provider
data = await provider.fetch_data_resilient("RELIANCE", "price")
historical = await provider.fetch_price_data("TCS")
volume_data = await provider.fetch_data_resilient("HDFCBANK", "volume")
```

## Usage Examples

### Basic Usage

```python
# All these work seamlessly:
await provider.fetch_data_resilient("RELIANCE", "price")      # Raw NSE symbol
await provider.fetch_data_resilient("TCS.NS", "volume")       # Yahoo NSE format
await provider.fetch_data_resilient("HDFCBANK.BO", "price")   # Yahoo BSE format
await provider.fetch_data_resilient("NIFTY", "price")         # Index by name
await provider.fetch_data_resilient("^NSEI", "price")         # Index Yahoo format
await provider.fetch_data_resilient("500325", "price")        # BSE numerical code
```

### Historical Data

```python
# Fetch historical price data
historical_data = await provider.fetch_price_data(
    symbol="RELIANCE",
    start_date="2024-01-01",
    end_date="2024-12-31",
    interval="1d"
)
```

### Backtesting

```python
from backend.backtesting.data_loader import get_historical_ohlcv

# Backtesting automatically uses normalized symbols
ohlcv_data = get_historical_ohlcv("TCS", "2024-01-01", "2024-12-31")
```

## Provider-Specific Behavior

### Yahoo Finance

- Raw symbols get `.NS` suffix: `RELIANCE` → `RELIANCE.NS`
- Index names get converted: `NIFTY` → `^NSEI`
- Already formatted symbols pass through: `TCS.BO` → `TCS.BO`

### Alpha Vantage

- Removes exchange suffixes: `RELIANCE.NS` → `RELIANCE`
- Index symbols get special mapping: `^NSEI` → `NSEI.NSE`
- Raw symbols pass through: `TCS` → `TCS`

### Polygon/Finnhub

- Similar to Alpha Vantage behavior
- Removes exchange suffixes for API compatibility

## Symbol Detection Logic

The system automatically detects Indian symbols using:

1. **Exchange suffixes**: `.NS`, `.BO`
2. **Index prefixes**: `^NSEI`, `^BSESN`
3. **Known stocks**: Major Indian stocks in internal database
4. **BSE codes**: 6-digit numerical codes
5. **Pattern matching**: Indian symbol naming patterns

## Error Handling

### Invalid Symbols

```python
# These will be caught during validation:
invalid_symbols = [
    "INVALID@SYMBOL",     # Invalid characters
    "",                   # Empty symbol
    "TOOLONGNAME123456",  # Too long
    "12345",             # Wrong length for BSE code
]
```

### Fallback Behavior

- If symbol normalization fails, the original symbol is used
- Detailed error messages provided for debugging
- Logging captures all normalization events

## Configuration

### Major Stocks Database

The system includes a database of major Indian stocks:

```python
MAJOR_STOCKS = {
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "SBIN", "LT", "ITC", "KOTAKBANK",
    # ... and more
}
```

### Index Mapping

```python
INDIAN_INDICES = {
    "NIFTY": "^NSEI",
    "NIFTY50": "^NSEI",
    "SENSEX": "^BSESN",
    "BANKNIFTY": "^NSEBANK",
    "INDIAVIX": "^INDIAVIX",
}
```

## Integration Points

### 1. Data Providers

- `UnifiedDataProvider`: Central normalization
- `YahooFinanceProvider`: Yahoo-specific normalization
- `AlphaVantageProvider`: Alpha Vantage-specific normalization

### 2. Validation Layer

- `SymbolRequest`: Basic validation
- `EnhancedSymbolRequest`: Provider-aware validation

### 3. Backtesting System

- `BacktestDataLoader`: Uses normalized symbols for historical data

### 4. API Endpoints

- All API endpoints automatically benefit from symbol normalization
- No changes needed in frontend code

## Testing

Run the test suite to verify functionality:

```bash
cd d:\Zion
python test_indian_equity_system.py
```

This tests:

- Symbol validation and normalization
- Provider-specific formatting
- Data fetching integration
- Error handling
- Edge cases

## Troubleshooting

### Common Issues

1. **Symbol not recognized as Indian**
   - Add to `MAJOR_STOCKS` database if it's a major stock
   - Verify symbol format matches Indian patterns

2. **API calls failing**
   - Check that normalized symbols are correct for each provider
   - Verify API keys are configured for data providers

3. **Backtesting data not found**
   - Ensure symbol exists on NSE (Yahoo Finance requirement)
   - Try BSE format if NSE data unavailable

### Debugging

```python
from backend.utils.symbol_normalizer import IndianEquitySymbolNormalizer

# Debug symbol detection
print(IndianEquitySymbolNormalizer.is_indian_symbol("YOUR_SYMBOL"))
print(IndianEquitySymbolNormalizer.detect_exchange("YOUR_SYMBOL"))
print(IndianEquitySymbolNormalizer.get_base_symbol("YOUR_SYMBOL"))
```

## Future Enhancements

1. **Additional Exchanges**: Support for other Indian exchanges
2. **Commodity Symbols**: Support for MCX commodity symbols
3. **Derivative Symbols**: Support for F&O symbols
4. **Real-time Validation**: Live symbol validation against exchange databases
5. **Symbol Search**: Enhanced search functionality for discovering symbols

---

This system ensures that the Zion trading platform can handle any Indian equity symbol seamlessly, providing a robust foundation for Indian market trading operations.
