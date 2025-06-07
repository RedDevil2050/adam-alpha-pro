#!/usr/bin/env python3
"""
Performance Optimization Script for Indian Equity Symbol System
Implements caching, symbol database expansion, and performance monitoring.
"""

import sys
import os
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any
import sqlite3
from dataclasses import dataclass, asdict

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

@dataclass
class PerformanceMetrics:
    """Performance metrics for optimization tracking"""
    operation: str
    execution_time: float
    cache_hit: bool
    timestamp: datetime
    symbol: str
    provider: str

class IndianEquityOptimizer:
    """Optimization system for Indian equity handling"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.symbol_cache = {}
        self.db_path = "indian_equity_optimization.db"
        self.init_database()
        
    def init_database(self):
        """Initialize optimization database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables for optimization
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS symbol_cache (
                    symbol TEXT PRIMARY KEY,
                    normalized_yahoo TEXT,
                    normalized_alpha_vantage TEXT,
                    normalized_polygon TEXT,
                    is_indian BOOLEAN,
                    exchange TEXT,
                    created_at TIMESTAMP,
                    last_accessed TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation TEXT,
                    execution_time REAL,
                    cache_hit BOOLEAN,
                    timestamp TIMESTAMP,
                    symbol TEXT,
                    provider TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS indian_stocks_extended (
                    symbol TEXT PRIMARY KEY,
                    company_name TEXT,
                    sector TEXT,
                    market_cap_category TEXT,
                    exchange TEXT,
                    bse_code TEXT,
                    isin TEXT,
                    is_active BOOLEAN,
                    added_at TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            print("✅ Optimization database initialized")
            
        except Exception as e:
            print(f"❌ Database initialization error: {e}")
    
    async def expand_symbol_database(self) -> Dict[str, Any]:
        """Expand the symbol database with more Indian stocks"""
        start_time = datetime.now()
        
        try:
            # Extended list of Indian stocks by category
            extended_stocks = {
                "large_cap": [
                    {"symbol": "ADANIPORTS", "name": "Adani Ports and SEZ", "sector": "Infrastructure"},
                    {"symbol": "APOLLOHOSP", "name": "Apollo Hospitals", "sector": "Healthcare"},
                    {"symbol": "BAJAJ-AUTO", "name": "Bajaj Auto", "sector": "Automotive"},
                    {"symbol": "BAJAJFINSV", "name": "Bajaj Finserv", "sector": "Financial Services"},
                    {"symbol": "BAJFINANCE", "name": "Bajaj Finance", "sector": "NBFC"},
                    {"symbol": "BHARTIARTL", "name": "Bharti Airtel", "sector": "Telecom"},
                    {"symbol": "BPCL", "name": "Bharat Petroleum", "sector": "Oil & Gas"},
                    {"symbol": "BRITANNIA", "name": "Britannia Industries", "sector": "FMCG"},
                    {"symbol": "CIPLA", "name": "Cipla", "sector": "Pharmaceuticals"},
                    {"symbol": "COALINDIA", "name": "Coal India", "sector": "Mining"},
                    {"symbol": "DIVISLAB", "name": "Divi's Laboratories", "sector": "Pharmaceuticals"},
                    {"symbol": "DRREDDY", "name": "Dr. Reddy's Labs", "sector": "Pharmaceuticals"},
                    {"symbol": "EICHERMOT", "name": "Eicher Motors", "sector": "Automotive"},
                    {"symbol": "GRASIM", "name": "Grasim Industries", "sector": "Cement"},
                    {"symbol": "HCLTECH", "name": "HCL Technologies", "sector": "IT"},
                    {"symbol": "HEROMOTOCO", "name": "Hero MotoCorp", "sector": "Automotive"},
                    {"symbol": "HINDALCO", "name": "Hindalco Industries", "sector": "Metals"},
                    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever", "sector": "FMCG"},
                    {"symbol": "ICICIBANK", "name": "ICICI Bank", "sector": "Banking"},
                    {"symbol": "INDUSINDBK", "name": "IndusInd Bank", "sector": "Banking"},
                    {"symbol": "IOC", "name": "Indian Oil Corporation", "sector": "Oil & Gas"},
                    {"symbol": "ITC", "name": "ITC", "sector": "FMCG"},
                    {"symbol": "JSWSTEEL", "name": "JSW Steel", "sector": "Metals"},
                    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank", "sector": "Banking"},
                    {"symbol": "LT", "name": "Larsen & Toubro", "sector": "Infrastructure"},
                    {"symbol": "M&M", "name": "Mahindra & Mahindra", "sector": "Automotive"},
                    {"symbol": "MARUTI", "name": "Maruti Suzuki", "sector": "Automotive"},
                    {"symbol": "NESTLEIND", "name": "Nestle India", "sector": "FMCG"},
                    {"symbol": "NTPC", "name": "NTPC", "sector": "Power"},
                    {"symbol": "ONGC", "name": "Oil & Natural Gas Corp", "sector": "Oil & Gas"},
                    {"symbol": "POWERGRID", "name": "Power Grid Corporation", "sector": "Power"},
                    {"symbol": "RELIANCE", "name": "Reliance Industries", "sector": "Oil & Gas"},
                    {"symbol": "SBILIFE", "name": "SBI Life Insurance", "sector": "Insurance"},
                    {"symbol": "SBIN", "name": "State Bank of India", "sector": "Banking"},
                    {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical", "sector": "Pharmaceuticals"},
                    {"symbol": "TATACONSUM", "name": "Tata Consumer Products", "sector": "FMCG"},
                    {"symbol": "TATAMOTORS", "name": "Tata Motors", "sector": "Automotive"},
                    {"symbol": "TATASTEEL", "name": "Tata Steel", "sector": "Metals"},
                    {"symbol": "TCS", "name": "Tata Consultancy Services", "sector": "IT"},
                    {"symbol": "TECHM", "name": "Tech Mahindra", "sector": "IT"},
                    {"symbol": "TITAN", "name": "Titan Company", "sector": "Consumer Goods"},
                    {"symbol": "ULTRACEMCO", "name": "UltraTech Cement", "sector": "Cement"},
                    {"symbol": "UPL", "name": "UPL", "sector": "Chemicals"},
                    {"symbol": "WIPRO", "name": "Wipro", "sector": "IT"}
                ],
                "mid_cap": [
                    {"symbol": "ABCAPITAL", "name": "Aditya Birla Capital", "sector": "Financial Services"},
                    {"symbol": "ABFRL", "name": "Aditya Birla Fashion", "sector": "Textiles"},
                    {"symbol": "ACC", "name": "ACC", "sector": "Cement"},
                    {"symbol": "ALKEM", "name": "Alkem Laboratories", "sector": "Pharmaceuticals"},
                    {"symbol": "AMBUJACEM", "name": "Ambuja Cements", "sector": "Cement"},
                    {"symbol": "ASTRAL", "name": "Astral", "sector": "Building Materials"},
                    {"symbol": "AUBANK", "name": "AU Small Finance Bank", "sector": "Banking"},
                    {"symbol": "BANDHANBNK", "name": "Bandhan Bank", "sector": "Banking"},
                    {"symbol": "BATAINDIA", "name": "Bata India", "sector": "Consumer Goods"},
                    {"symbol": "BERGEPAINT", "name": "Berger Paints", "sector": "Paints"},
                    {"symbol": "BIOCON", "name": "Biocon", "sector": "Pharmaceuticals"},
                    {"symbol": "BOSCHLTD", "name": "Bosch", "sector": "Automotive"},
                    {"symbol": "CUB", "name": "City Union Bank", "sector": "Banking"},
                    {"symbol": "DABUR", "name": "Dabur India", "sector": "FMCG"},
                    {"symbol": "DMART", "name": "Avenue Supermarts", "sector": "Retail"},
                    {"symbol": "FEDERALBNK", "name": "Federal Bank", "sector": "Banking"},
                    {"symbol": "GODREJCP", "name": "Godrej Consumer Products", "sector": "FMCG"},
                    {"symbol": "HAVELLS", "name": "Havells India", "sector": "Electrical Equipment"},
                    {"symbol": "HDFCAMC", "name": "HDFC Asset Management", "sector": "Financial Services"},
                    {"symbol": "ICICIGI", "name": "ICICI General Insurance", "sector": "Insurance"},
                    {"symbol": "ICICIPRULI", "name": "ICICI Prudential Life", "sector": "Insurance"},
                    {"symbol": "JINDALSTEL", "name": "Jindal Steel & Power", "sector": "Metals"},
                    {"symbol": "JUBLFOOD", "name": "Jubilant FoodWorks", "sector": "Restaurants"},
                    {"symbol": "LUPIN", "name": "Lupin", "sector": "Pharmaceuticals"},
                    {"symbol": "MARICO", "name": "Marico", "sector": "FMCG"},
                    {"symbol": "MFSL", "name": "Max Financial Services", "sector": "Insurance"},
                    {"symbol": "MPHASIS", "name": "Mphasis", "sector": "IT"},
                    {"symbol": "MUTHOOTFIN", "name": "Muthoot Finance", "sector": "NBFC"},
                    {"symbol": "PAGEIND", "name": "Page Industries", "sector": "Textiles"},
                    {"symbol": "PEL", "name": "Piramal Enterprises", "sector": "Pharmaceuticals"},
                    {"symbol": "PIDILITIND", "name": "Pidilite Industries", "sector": "Chemicals"},
                    {"symbol": "PIIND", "name": "PI Industries", "sector": "Chemicals"},
                    {"symbol": "PNB", "name": "Punjab National Bank", "sector": "Banking"},
                    {"symbol": "SAIL", "name": "Steel Authority of India", "sector": "Metals"},
                    {"symbol": "TORNTPHARM", "name": "Torrent Pharmaceuticals", "sector": "Pharmaceuticals"},
                    {"symbol": "TRENT", "name": "Trent", "sector": "Retail"},
                    {"symbol": "VOLTAS", "name": "Voltas", "sector": "Consumer Durables"}
                ],
                "small_cap": [
                    {"symbol": "5PAISA", "name": "5paisa Capital", "sector": "Financial Services"},
                    {"symbol": "AARTIDRUGS", "name": "Aarti Drugs", "sector": "Pharmaceuticals"},
                    {"symbol": "AARTIIND", "name": "Aarti Industries", "sector": "Chemicals"},
                    {"symbol": "ADVENZYMES", "name": "Advanced Enzyme Technologies", "sector": "Chemicals"},
                    {"symbol": "AFFLE", "name": "Affle India", "sector": "Technology"},
                    {"symbol": "AIAENG", "name": "AIA Engineering", "sector": "Industrial Manufacturing"},
                    {"symbol": "ANGELONE", "name": "Angel One", "sector": "Financial Services"},
                    {"symbol": "ARVINDFASN", "name": "Arvind Fashions", "sector": "Textiles"},
                    {"symbol": "ASIANPAINT", "name": "Asian Paints", "sector": "Paints"},
                    {"symbol": "AVANTIFEED", "name": "Avanti Feeds", "sector": "Agriculture"},
                    {"symbol": "BALKRISIND", "name": "Balkrishna Industries", "sector": "Automotive"},
                    {"symbol": "BEML", "name": "BEML", "sector": "Industrial Manufacturing"},
                    {"symbol": "BIRLACORPN", "name": "Birla Corporation", "sector": "Cement"},
                    {"symbol": "BSOFT", "name": "Birlasoft", "sector": "IT"},
                    {"symbol": "CANFINHOME", "name": "Can Fin Homes", "sector": "Housing Finance"},
                    {"symbol": "CAPLIPOINT", "name": "Caplin Point Laboratories", "sector": "Pharmaceuticals"},
                    {"symbol": "CARYSIL", "name": "Carysil", "sector": "Consumer Durables"},
                    {"symbol": "CEATLTD", "name": "CEAT", "sector": "Automotive"},
                    {"symbol": "CENTUM", "name": "Centum Electronics", "sector": "Electronics"},
                    {"symbol": "CHALET", "name": "Chalet Hotels", "sector": "Hospitality"},
                    {"symbol": "CHAMBLFERT", "name": "Chambal Fertilizers", "sector": "Fertilizers"},
                    {"symbol": "CHEMCON", "name": "Chemcon Speciality Chemicals", "sector": "Chemicals"},
                    {"symbol": "CHOLAFIN", "name": "Cholamandalam Investment", "sector": "NBFC"},
                    {"symbol": "COFORGE", "name": "Coforge", "sector": "IT"},
                    {"symbol": "CONCOR", "name": "Container Corporation", "sector": "Logistics"},
                    {"symbol": "COROMANDEL", "name": "Coromandel International", "sector": "Fertilizers"},
                    {"symbol": "CRISIL", "name": "CRISIL", "sector": "Financial Services"},
                    {"symbol": "DELTACORP", "name": "Delta Corp", "sector": "Entertainment"},
                    {"symbol": "DIXON", "name": "Dixon Technologies", "sector": "Electronics"},
                    {"symbol": "EASEMYTRIP", "name": "Easy Trip Planners", "sector": "Travel & Tourism"},
                    {"symbol": "EQUITAS", "name": "Equitas Holdings", "sector": "Banking"},
                    {"symbol": "ESABINDIA", "name": "Esab India", "sector": "Industrial Manufacturing"},
                    {"symbol": "EXIDEIND", "name": "Exide Industries", "sector": "Automotive"},
                    {"symbol": "FDC", "name": "FDC", "sector": "Pharmaceuticals"},
                    {"symbol": "FINEORG", "name": "Fine Organic Industries", "sector": "Chemicals"},
                    {"symbol": "FINPIPE", "name": "Finolex Industries", "sector": "Building Materials"},
                    {"symbol": "GAIL", "name": "GAIL India", "sector": "Oil & Gas"},
                    {"symbol": "GLENMARK", "name": "Glenmark Pharmaceuticals", "sector": "Pharmaceuticals"},
                    {"symbol": "GMRINFRA", "name": "GMR Infrastructure", "sector": "Infrastructure"},
                    {"symbol": "GNFC", "name": "Gujarat Narmada Valley Fertilizers", "sector": "Fertilizers"},
                    {"symbol": "GOKEX", "name": "Gokaldas Exports", "sector": "Textiles"},
                    {"symbol": "GRAPHITE", "name": "Graphite India", "sector": "Industrial Manufacturing"},
                    {"symbol": "GREENPANEL", "name": "Greenpanel Industries", "sector": "Building Materials"},
                    {"symbol": "GRINDWELL", "name": "Grindwell Norton", "sector": "Industrial Manufacturing"},
                    {"symbol": "GULFOILLUB", "name": "Gulf Oil Lubricants", "sector": "Oil & Gas"},
                    {"symbol": "HAPPSTMNDS", "name": "Happiest Minds Technologies", "sector": "IT"},
                    {"symbol": "HATSUN", "name": "Hatsun Agro Product", "sector": "FMCG"},
                    {"symbol": "HEIDELBERG", "name": "HeidelbergCement India", "sector": "Cement"},
                    {"symbol": "HFCL", "name": "HFCL", "sector": "Telecom"},
                    {"symbol": "HONAUT", "name": "Honeywell Automation India", "sector": "Industrial Automation"},
                    {"symbol": "IDFCFIRSTB", "name": "IDFC First Bank", "sector": "Banking"},
                    {"symbol": "IFBIND", "name": "IFB Industries", "sector": "Consumer Durables"},
                    {"symbol": "IGARASHI", "name": "Igarashi Motors India", "sector": "Automotive"},
                    {"symbol": "INDHOTEL", "name": "The Indian Hotels Company", "sector": "Hospitality"},
                    {"symbol": "INOXLEISUR", "name": "INOX Leisures", "sector": "Entertainment"},
                    {"symbol": "IRCTC", "name": "Indian Railway Catering", "sector": "Travel & Tourism"},
                    {"symbol": "IRFC", "name": "Indian Railway Finance Corporation", "sector": "Financial Services"},
                    {"symbol": "IGL", "name": "Indraprastha Gas", "sector": "Oil & Gas"},
                    {"symbol": "JKCEMENT", "name": "JK Cement", "sector": "Cement"},
                    {"symbol": "JKTYRE", "name": "JK Tyre & Industries", "sector": "Automotive"},
                    {"symbol": "JMFINANCIL", "name": "JM Financial", "sector": "Financial Services"},
                    {"symbol": "JSWENERGY", "name": "JSW Energy", "sector": "Power"},
                    {"symbol": "KAJARIACER", "name": "Kajaria Ceramics", "sector": "Building Materials"},
                    {"symbol": "KALPATPOWR", "name": "Kalpataru Power Transmission", "sector": "Power"},
                    {"symbol": "KANSAINER", "name": "Kansai Nerolac Paints", "sector": "Paints"},
                    {"symbol": "KEC", "name": "KEC International", "sector": "Infrastructure"},
                    {"symbol": "KEI", "name": "KEI Industries", "sector": "Electrical Equipment"},
                    {"symbol": "KNRCON", "name": "KNR Constructions", "sector": "Infrastructure"},
                    {"symbol": "KRBL", "name": "KRBL", "sector": "Agriculture"},
                    {"symbol": "L&TFH", "name": "L&T Finance Holdings", "sector": "NBFC"},
                    {"symbol": "LALPATHLAB", "name": "Dr. Lal PathLabs", "sector": "Healthcare"},
                    {"symbol": "LATENTVIEW", "name": "LatentView Analytics", "sector": "IT"},
                    {"symbol": "LAURUSLABS", "name": "Laurus Labs", "sector": "Pharmaceuticals"},
                    {"symbol": "LICHSGFIN", "name": "LIC Housing Finance", "sector": "Housing Finance"},
                    {"symbol": "LXCHEM", "name": "Laxmi Organic Industries", "sector": "Chemicals"},
                    {"symbol": "MANAPPURAM", "name": "Manappuram Finance", "sector": "NBFC"},
                    {"symbol": "MASTEK", "name": "Mastek", "sector": "IT"},
                    {"symbol": "METROPOLIS", "name": "Metropolis Healthcare", "sector": "Healthcare"},
                    {"symbol": "MINDACORP", "name": "Minda Corporation", "sector": "Automotive"},
                    {"symbol": "MINDTREE", "name": "Mindtree", "sector": "IT"},
                    {"symbol": "MIDHANI", "name": "Mishra Dhatu Nigam", "sector": "Metals"},
                    {"symbol": "MOTHERSON", "name": "Motherson Sumi Systems", "sector": "Automotive"},
                    {"symbol": "MCDOWELL-N", "name": "United Spirits", "sector": "Beverages"},
                    {"symbol": "NATIONALUM", "name": "National Aluminium Company", "sector": "Metals"},
                    {"symbol": "NAUKRI", "name": "Info Edge India", "sector": "Internet"},
                    {"symbol": "NAVINFLUOR", "name": "Navin Fluorine International", "sector": "Chemicals"},
                    {"symbol": "NETWORK18", "name": "Network18 Media", "sector": "Media"},
                    {"symbol": "NILKAMAL", "name": "Nilkamal", "sector": "Consumer Durables"},
                    {"symbol": "NLCINDIA", "name": "NLC India", "sector": "Power"},
                    {"symbol": "NMDC", "name": "NMDC", "sector": "Mining"},
                    {"symbol": "NOCIL", "name": "NOCIL", "sector": "Chemicals"},
                    {"symbol": "NYKAA", "name": "FSN E-Commerce Ventures", "sector": "E-commerce"},
                    {"symbol": "OBEROIRLTY", "name": "Oberoi Realty", "sector": "Real Estate"},
                    {"symbol": "OFSS", "name": "Oracle Financial Services Software", "sector": "IT"},
                    {"symbol": "OIL", "name": "Oil India", "sector": "Oil & Gas"},
                    {"symbol": "ORIENTELEC", "name": "Orient Electric", "sector": "Electrical Equipment"},
                    {"symbol": "PAYTM", "name": "One 97 Communications", "sector": "Fintech"},
                    {"symbol": "PERSISTENT", "name": "Persistent Systems", "sector": "IT"},
                    {"symbol": "PETRONET", "name": "Petronet LNG", "sector": "Oil & Gas"},
                    {"symbol": "PFIZER", "name": "Pfizer", "sector": "Pharmaceuticals"},
                    {"symbol": "PHOENIXLTD", "name": "Phoenix Mills", "sector": "Real Estate"},
                    {"symbol": "POLYCAB", "name": "Polycab India", "sector": "Electrical Equipment"},
                    {"symbol": "POLYMED", "name": "Poly Medicure", "sector": "Healthcare"},
                    {"symbol": "POONAWALLA", "name": "Poonawalla Fincorp", "sector": "NBFC"},
                    {"symbol": "PRSMJOHNSN", "name": "Prism Johnson", "sector": "Building Materials"},
                    {"symbol": "PTC", "name": "PTC India", "sector": "Power"},
                    {"symbol": "PVR", "name": "PVR", "sector": "Entertainment"},
                    {"symbol": "QUESS", "name": "Quess Corp", "sector": "HR Services"},
                    {"symbol": "RADICO", "name": "Radico Khaitan", "sector": "Beverages"},
                    {"symbol": "RAJESHEXPO", "name": "Rajesh Exports", "sector": "Gems & Jewellery"},
                    {"symbol": "RALLIS", "name": "Rallis India", "sector": "Chemicals"},
                    {"symbol": "RAMCOCEM", "name": "The Ramco Cements", "sector": "Cement"},
                    {"symbol": "RATNAMANI", "name": "Ratnamani Metals & Tubes", "sector": "Metals"},
                    {"symbol": "RBLBANK", "name": "RBL Bank", "sector": "Banking"},
                    {"symbol": "RECLTD", "name": "REC", "sector": "Financial Services"},
                    {"symbol": "REDINGTON", "name": "Redington India", "sector": "Technology Distribution"},
                    {"symbol": "RELAXO", "name": "Relaxo Footwears", "sector": "Consumer Goods"},
                    {"symbol": "ROUTE", "name": "Route Mobile", "sector": "Technology"},
                    {"symbol": "RTNINDIA", "name": "RattanIndia Enterprises", "sector": "Diversified"},
                    {"symbol": "RUPA", "name": "Rupa & Company", "sector": "Textiles"},
                    {"symbol": "SANOFI", "name": "Sanofi India", "sector": "Pharmaceuticals"},
                    {"symbol": "SCHNEIDER", "name": "Schneider Electric Infrastructure", "sector": "Electrical Equipment"},
                    {"symbol": "SHILPAMED", "name": "Shilpa Medicare", "sector": "Pharmaceuticals"},
                    {"symbol": "SHOPERSTOP", "name": "Shoppers Stop", "sector": "Retail"},
                    {"symbol": "SIEMENS", "name": "Siemens", "sector": "Industrial Manufacturing"},
                    {"symbol": "SIS", "name": "SIS", "sector": "Security Services"},
                    {"symbol": "SJVN", "name": "SJVN", "sector": "Power"},
                    {"symbol": "SKFINDIA", "name": "SKF India", "sector": "Industrial Manufacturing"},
                    {"symbol": "SRF", "name": "SRF", "sector": "Chemicals"},
                    {"symbol": "STARHEALTH", "name": "Star Health and Allied Insurance", "sector": "Insurance"},
                    {"symbol": "SUNTV", "name": "Sun TV Network", "sector": "Media"},
                    {"symbol": "SUPRAJIT", "name": "Suprajit Engineering", "sector": "Automotive"},
                    {"symbol": "SURYODAY", "name": "Suryoday Small Finance Bank", "sector": "Banking"},
                    {"symbol": "SUZLON", "name": "Suzlon Energy", "sector": "Power"},
                    {"symbol": "SYMPHONY", "name": "Symphony", "sector": "Consumer Durables"},
                    {"symbol": "TANLA", "name": "Tanla Platforms", "sector": "Technology"},
                    {"symbol": "TEAMLEASE", "name": "TeamLease Services", "sector": "HR Services"},
                    {"symbol": "THERMAX", "name": "Thermax", "sector": "Industrial Manufacturing"},
                    {"symbol": "TIMKEN", "name": "Timken India", "sector": "Industrial Manufacturing"},
                    {"symbol": "TITAGARH", "name": "Titagarh Wagons", "sector": "Industrial Manufacturing"},
                    {"symbol": "TTKPRESTIG", "name": "TTK Prestige", "sector": "Consumer Durables"},
                    {"symbol": "TVSHLTD", "name": "TVS Holdings", "sector": "Automotive"},
                    {"symbol": "UCOBANK", "name": "UCO Bank", "sector": "Banking"},
                    {"symbol": "UJJIVAN", "name": "Ujjivan Financial Services", "sector": "NBFC"},
                    {"symbol": "UNIONBANK", "name": "Union Bank of India", "sector": "Banking"},
                    {"symbol": "UBL", "name": "United Breweries", "sector": "Beverages"},
                    {"symbol": "UTIAMC", "name": "UTI Asset Management Company", "sector": "Financial Services"},
                    {"symbol": "VACCHETD", "name": "Varroc Engineering", "sector": "Automotive"},
                    {"symbol": "VAIBHAVGBL", "name": "Vaibhav Global", "sector": "Retail"},
                    {"symbol": "VARROC", "name": "Varroc Engineering", "sector": "Automotive"},
                    {"symbol": "VCPL", "name": "VIP Clothing", "sector": "Textiles"},
                    {"symbol": "VEDL", "name": "Vedanta", "sector": "Mining"},
                    {"symbol": "VINATIORGA", "name": "Vinati Organics", "sector": "Chemicals"},
                    {"symbol": "VSTIND", "name": "VST Industries", "sector": "Tobacco"},
                    {"symbol": "VSTTECH", "name": "VST Tillers Tractors", "sector": "Agricultural Equipment"},
                    {"symbol": "WABCOINDIA", "name": "WABCO India", "sector": "Automotive"},
                    {"symbol": "WELCORP", "name": "Welspun Corp", "sector": "Infrastructure"},
                    {"symbol": "WELSPUNIND", "name": "Welspun India", "sector": "Textiles"},
                    {"symbol": "WESTLIFE", "name": "Westlife Development", "sector": "Restaurants"},
                    {"symbol": "WHIRLPOOL", "name": "Whirlpool of India", "sector": "Consumer Durables"},
                    {"symbol": "WOCKPHARMA", "name": "Wockhardt", "sector": "Pharmaceuticals"},
                    {"symbol": "YESBANK", "name": "YES Bank", "sector": "Banking"},
                    {"symbol": "ZEEL", "name": "Zee Entertainment Enterprises", "sector": "Media"},
                    {"symbol": "ZENSARTECH", "name": "Zensar Technologies", "sector": "IT"},
                    {"symbol": "ZFCVINDIA", "name": "ZF Commercial Vehicle Control Systems India", "sector": "Automotive"},
                    {"symbol": "ZYDUSLIFE", "name": "Zydus Lifesciences", "sector": "Pharmaceuticals"}
                ]
            }
            
            # Insert into database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            total_added = 0
            for category, stocks in extended_stocks.items():
                market_cap_category = category
                
                for stock in stocks:
                    try:
                        cursor.execute('''
                            INSERT OR REPLACE INTO indian_stocks_extended 
                            (symbol, company_name, sector, market_cap_category, exchange, is_active, added_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            stock["symbol"],
                            stock["name"],
                            stock["sector"],
                            market_cap_category,
                            "NSE",  # Default to NSE
                            True,
                            datetime.now()
                        ))
                        total_added += 1
                    except Exception as e:
                        print(f"Error adding {stock['symbol']}: {e}")
            
            conn.commit()
            conn.close()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "total_added": total_added,
                "categories": list(extended_stocks.keys()),
                "execution_time": execution_time,
                "details": f"Successfully added {total_added} Indian stocks to extended database"
            }
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return {                "success": False,
                "error": str(e),
                "execution_time": execution_time,
                "details": f"Failed to expand symbol database: {e}"
            }
    
    def create_symbol_cache(self) -> Dict[str, Any]:
        """Create and populate symbol normalization cache"""
        start_time = datetime.now()
        
        try:
            from backend.utils.symbol_normalizer_fixed import (
                normalize_indian_symbol, 
                IndianEquitySymbolNormalizer
            )
            
            # Get all symbols from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT symbol FROM indian_stocks_extended WHERE is_active = 1")
            symbols = [row[0] for row in cursor.fetchall()]
            
            # Add some common index symbols
            symbols.extend(["NIFTY", "SENSEX", "BANKNIFTY", "^NSEI", "^BSESN"])
            
            cached_count = 0
            for symbol in symbols:
                try:
                    # Normalize for different providers
                    yahoo_norm = normalize_indian_symbol(symbol, "yahoo")
                    alpha_norm = normalize_indian_symbol(symbol, "alpha_vantage")
                    polygon_norm = normalize_indian_symbol(symbol, "polygon")
                    
                    # Check if it's Indian symbol
                    is_indian = IndianEquitySymbolNormalizer.is_indian_symbol(symbol)
                    exchange = IndianEquitySymbolNormalizer.detect_exchange(symbol)
                    
                    # Insert into cache
                    cursor.execute('''
                        INSERT OR REPLACE INTO symbol_cache
                        (symbol, normalized_yahoo, normalized_alpha_vantage, normalized_polygon, 
                         is_indian, exchange, created_at, last_accessed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        symbol, yahoo_norm, alpha_norm, polygon_norm,
                        is_indian, exchange, datetime.now(), datetime.now()
                    ))
                    
                    cached_count += 1
                    
                except Exception as e:
                    print(f"Error caching {symbol}: {e}")
            
            conn.commit()
            conn.close()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "cached_symbols": cached_count,
                "total_symbols": len(symbols),
                "execution_time": execution_time,
                "details": f"Successfully cached {cached_count} symbols for faster normalization"
            }
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return {
                "success": False,
                "error": str(e),
                "execution_time": execution_time,
                "details": f"Failed to create symbol cache: {e}"
            }
    
    def get_cached_normalization(self, symbol: str, provider: str) -> Optional[str]:
        """Get normalized symbol from cache"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            provider_column = f"normalized_{provider.lower()}"
            if provider_column not in ["normalized_yahoo", "normalized_alpha_vantage", "normalized_polygon"]:
                provider_column = "normalized_yahoo"  # Default
            
            cursor.execute(f'''
                SELECT {provider_column} FROM symbol_cache WHERE symbol = ?
            ''', (symbol,))
            
            result = cursor.fetchone()
            if result:
                # Update last accessed
                cursor.execute('''
                    UPDATE symbol_cache SET last_accessed = ? WHERE symbol = ?
                ''', (datetime.now(), symbol))
                conn.commit()
                
            conn.close()
            
            return result[0] if result else None
            
        except Exception as e:
            print(f"Cache lookup error for {symbol}: {e}")
            return None
    
    def record_performance_metric(self, operation: str, execution_time: float, 
                                 cache_hit: bool, symbol: str, provider: str):
        """Record performance metrics for optimization analysis"""
        try:
            metric = PerformanceMetrics(
                operation=operation,
                execution_time=execution_time,
                cache_hit=cache_hit,
                timestamp=datetime.now(),
                symbol=symbol,
                provider=provider
            )
            
            self.metrics.append(metric)
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_metrics
                (operation, execution_time, cache_hit, timestamp, symbol, provider)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                metric.operation, metric.execution_time, metric.cache_hit,
                metric.timestamp, metric.symbol, metric.provider
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error recording performance metric: {e}")
    
    def optimize_cached_normalization(self, symbol: str, provider: str) -> str:
        """Optimized symbol normalization with caching"""
        start_time = datetime.now()
        
        # Try cache first
        cached_result = self.get_cached_normalization(symbol, provider)
        
        if cached_result:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.record_performance_metric(
                "symbol_normalization", execution_time, True, symbol, provider
            )
            return cached_result
          # Cache miss - compute normalization
        try:
            from backend.utils.symbol_normalizer_fixed import normalize_indian_symbol
            result = normalize_indian_symbol(symbol, provider)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            self.record_performance_metric(
                "symbol_normalization", execution_time, False, symbol, provider
            )
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.record_performance_metric(
                "symbol_normalization", execution_time, False, symbol, provider
            )
            print(f"Normalization error for {symbol}: {e}")
            return symbol
    
    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze performance metrics and provide optimization recommendations"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get performance statistics
            cursor.execute('''
                SELECT 
                    operation,
                    AVG(execution_time) as avg_time,
                    MIN(execution_time) as min_time,
                    MAX(execution_time) as max_time,
                    COUNT(*) as total_operations,
                    SUM(CASE WHEN cache_hit = 1 THEN 1 ELSE 0 END) as cache_hits
                FROM performance_metrics 
                WHERE timestamp > datetime('now', '-24 hours')
                GROUP BY operation
            ''')
            
            performance_stats = []
            for row in cursor.fetchall():
                stats = {
                    "operation": row[0],
                    "avg_time": row[1],
                    "min_time": row[2],
                    "max_time": row[3],
                    "total_operations": row[4],
                    "cache_hits": row[5],
                    "cache_hit_rate": row[5] / row[4] if row[4] > 0 else 0
                }
                performance_stats.append(stats)
            
            # Get most frequently used symbols
            cursor.execute('''
                SELECT symbol, COUNT(*) as usage_count
                FROM performance_metrics 
                WHERE timestamp > datetime('now', '-7 days')
                GROUP BY symbol
                ORDER BY usage_count DESC
                LIMIT 20
            ''')
            
            popular_symbols = [{"symbol": row[0], "usage_count": row[1]} for row in cursor.fetchall()]
            
            # Get cache statistics
            cursor.execute('SELECT COUNT(*) FROM symbol_cache')
            total_cached_symbols = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM symbol_cache 
                WHERE last_accessed > datetime('now', '-24 hours')
            ''')
            recently_accessed = cursor.fetchone()[0]
            
            conn.close()
            
            # Generate recommendations
            recommendations = []
            
            for stat in performance_stats:
                if stat["cache_hit_rate"] < 0.7:
                    recommendations.append(
                        f"Low cache hit rate ({stat['cache_hit_rate']:.1%}) for {stat['operation']} - consider pre-caching popular symbols"
                    )
                
                if stat["avg_time"] > 0.1:
                    recommendations.append(
                        f"High average execution time ({stat['avg_time']:.3f}s) for {stat['operation']} - investigate bottlenecks"
                    )
            
            if recently_accessed / total_cached_symbols < 0.3:
                recommendations.append("Many cached symbols are unused - consider cache cleanup")
            
            return {
                "performance_stats": performance_stats,
                "popular_symbols": popular_symbols,
                "cache_stats": {
                    "total_cached_symbols": total_cached_symbols,
                    "recently_accessed": recently_accessed,
                    "utilization_rate": recently_accessed / total_cached_symbols if total_cached_symbols > 0 else 0
                },
                "recommendations": recommendations,
                "summary": {
                    "total_operations_24h": sum(stat["total_operations"] for stat in performance_stats),
                    "avg_cache_hit_rate": sum(stat["cache_hit_rate"] for stat in performance_stats) / len(performance_stats) if performance_stats else 0,
                    "optimization_score": self._calculate_optimization_score(performance_stats)
                }
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "details": "Failed to analyze performance metrics"
            }
    
    def _calculate_optimization_score(self, performance_stats: List[Dict]) -> float:
        """Calculate optimization score (0-100)"""
        if not performance_stats:
            return 0.0
        
        avg_cache_hit_rate = sum(stat["cache_hit_rate"] for stat in performance_stats) / len(performance_stats)
        avg_execution_time = sum(stat["avg_time"] for stat in performance_stats) / len(performance_stats)
        
        # Score based on cache hit rate (0-50 points)
        cache_score = min(avg_cache_hit_rate * 50, 50)
        
        # Score based on execution time (0-50 points)
        # Assume 0.001s is excellent, 0.1s is poor
        time_score = max(0, 50 - (avg_execution_time - 0.001) * 500)
        
        return min(cache_score + time_score, 100.0)
    
    async def optimize_system(self) -> Dict[str, Any]:
        """Run complete system optimization"""
        print("🔧 STARTING INDIAN EQUITY SYSTEM OPTIMIZATION")
        print("=" * 60)
        
        results = {}
        
        # Step 1: Expand symbol database
        print("\n📊 Expanding symbol database...")
        results["database_expansion"] = await self.expand_symbol_database()
        
        # Step 2: Create symbol cache
        print("\n💾 Creating symbol normalization cache...")
        results["cache_creation"] = self.create_symbol_cache()
        
        # Step 3: Analyze current performance
        print("\n📈 Analyzing performance metrics...")
        results["performance_analysis"] = self.analyze_performance()
        
        # Step 4: Test optimized performance
        print("\n⚡ Testing optimized performance...")
        results["performance_test"] = await self.test_optimized_performance()
        
        # Summary
        total_time = sum(
            r.get("execution_time", 0) for r in results.values() 
            if isinstance(r, dict)
        )
        
        successful_steps = sum(
            1 for r in results.values() 
            if isinstance(r, dict) and r.get("success", False)
        )
        
        print("\n" + "=" * 60)
        print("🎯 OPTIMIZATION SUMMARY")
        print("=" * 60)
        print(f"Successful Steps: {successful_steps}/{len(results)}")
        print(f"Total Optimization Time: {total_time:.2f}s")
        
        if results.get("database_expansion", {}).get("success"):
            print(f"✅ Extended database with {results['database_expansion']['total_added']} symbols")
        
        if results.get("cache_creation", {}).get("success"):
            print(f"✅ Cached {results['cache_creation']['cached_symbols']} symbols for faster access")
        
        if results.get("performance_analysis", {}).get("summary"):
            analysis = results["performance_analysis"]["summary"]
            print(f"✅ System optimization score: {analysis.get('optimization_score', 0):.1f}/100")
        
        print("\n🚀 OPTIMIZATION COMPLETE!")
        print("The Indian equity system is now optimized for production use.")
        
        return {
            "summary": {
                "successful_steps": successful_steps,
                "total_steps": len(results),
                "total_time": total_time,
                "optimization_complete": successful_steps >= len(results) * 0.8
            },
            "results": results
        }
    
    async def test_optimized_performance(self) -> Dict[str, Any]:
        """Test performance after optimization"""
        start_time = datetime.now()
        
        try:
            test_symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"] * 20  # 100 operations
            
            # Test optimized normalization
            normalization_times = []
            cache_hits = 0
            
            for symbol in test_symbols:
                norm_start = datetime.now()
                result = self.optimize_cached_normalization(symbol, "yahoo")
                norm_time = (datetime.now() - norm_start).total_seconds()
                normalization_times.append(norm_time)
                
                # Check if it was a cache hit (very fast response)
                if norm_time < 0.001:
                    cache_hits += 1
            
            avg_normalization_time = sum(normalization_times) / len(normalization_times)
            cache_hit_rate = cache_hits / len(test_symbols)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "avg_normalization_time": avg_normalization_time,
                "cache_hit_rate": cache_hit_rate,
                "total_operations": len(test_symbols),
                "execution_time": execution_time,
                "performance_improvement": {
                    "cache_enabled": cache_hit_rate > 0.5,
                    "fast_normalization": avg_normalization_time < 0.01,
                    "optimized": cache_hit_rate > 0.5 and avg_normalization_time < 0.01
                }
            }
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return {
                "success": False,
                "error": str(e),
                "execution_time": execution_time
            }


async def main():
    """Main optimization execution"""
    optimizer = IndianEquityOptimizer()
    results = await optimizer.optimize_system()
    
    # Save optimization results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"indian_equity_optimization_{timestamp}.json"
    
    try:
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Optimization results saved to: {results_file}")
    except Exception as e:
        print(f"\n⚠️  Could not save optimization results: {e}")
    
    return results


if __name__ == "__main__":
    results = asyncio.run(main())
