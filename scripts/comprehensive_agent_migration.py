"""
Comprehensive Agent Migration Script
===================================

Moves ALL agents in the backend directory to the new organized structure
based on their functional categories.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List
from loguru import logger

class ComprehensiveAgentMigrator:
    """Migrates all agents to new directory structure"""
    
    def __init__(self, base_path: str = "d:/Zion"):
        self.base_path = Path(base_path)
        self.backend_path = self.base_path / "backend"
        
        # Define comprehensive agent categorization
        self.agent_categories = {
            # Data Collection Agents
            "data_collectors/web_scrapers": [
                "agents/stealth/moneycontrol_agent.py",
                "agents/stealth/trendlyne_agent.py", 
                "agents/stealth/stockedge_agent.py",
                "agents/stealth/screener_agent.py",
                "agents/stealth/tickertape_agent.py",
                "agents/stealth/tickertape_agent_fixed.py",
                "agents/stealth/tradingview_agent.py",
                "agents/stealth/tijori_agent.py",
                "agents/stealth/zerodha_agent.py"
            ],
            
            "data_collectors/api_providers": [
                # API-based data providers (to be created)
            ],
            
            # Technical Analysis Agents
            "analysis/technical": [
                "agents/technical/bollinger_band_agent.py",
                "agents/technical/bollinger_agent.py",
                "agents/technical/adx_agent.py",
                "agents/technical/stochastic_oscillator_agent.py",
                "agents/technical/supertrend_agent.py",
                "agents/technical/stochastic_agent.py",
                "agents/technical/sma_agent.py",
                "agents/technical/rsi_agent.py",
                "agents/technical/moving_average_agent.py",
                "agents/technical/momentum_agent.py",
                "agents/technical/ma_crossover_agent.py",
                "agents/technical/macd_agent.py",
                "agents/technical/volume_spike_agent.py",
                "agents/technical/trend_strength_agent.py"
            ],
            
            # Fundamental Analysis Agents
            "analysis/fundamental": [
                "agents/valuation/earnings_yield_agent.py",
                "agents/valuation/dividend_yield_agent.py",
                "agents/valuation/pb_ratio_agent.py",
                "agents/valuation/peg_ratio_agent.py",
                "agents/valuation/intrinsic_composite_agent.py",
                "agents/valuation/ev_ebitda_agent.py",
                "agents/valuation/eps_agent.py",
                "agents/valuation/dividend_agent.py",
                "agents/valuation/dcf_agent.py",
                "agents/valuation/book_to_market_agent.py",
                "agents/valuation/pe_ratio_agent.py",
                "agents/valuation/pfcf_ratio_agent.py",
                "agents/valuation/reverse_dcf_agent.py",
                "agents/valuation/price_to_sales_agent.py",
                "agents/valuation/price_to_book_agent.py",
                "agents/valuation/price_target_agent.py",
                "agents/dividend_agent.py"
            ],
            
            # Market Analysis Agents
            "analysis/market": [
                "agents/market/correlation_agent.py",
                "agents/market/liquidity_agent.py",
                "agents/market/volatility_agent.py",
                "agents/market/regime_agent.py",
                "agents/market/momentum_agent.py",
                "agents/market/market_regime_agent.py",
                "agents/market_regime_agent.py"
            ],
            
            # Sentiment Analysis Agents
            "analysis/sentiment": [
                "agents/sentiment/twitter_sentiment_agent.py",
                "agents/sentiment/transcript_sentiment_agent.py",
                "agents/sentiment/social_sentiment_agent.py",
                "agents/sentiment/overall_sentiment_agent.py",
                "agents/sentiment/news_volume_spike_agent.py",
                "agents/sentiment/news_sentiment_agent.py"
            ],
            
            # Risk Management Agents
            "risk_management": [
                "agents/risk/max_drawdown_agent.py",
                "agents/risk/drawdown_agent.py",
                "agents/risk/risk_core_agent.py",
                "agents/risk/beta_agent.py",
                "agents/risk/sharpe_agent.py",
                "agents/risk/volatility_level_agent.py",
                "agents/risk/var_agent.py"
            ],
            
            # AI/ML Intelligence Agents
            "intelligence/ai_ml": [
                "agents/intelligence/reasoning_chain_agent.py",
                "agents/intelligence/smart_explanation_agent.py",
                "agents/intelligence/price_target_agent.py",
                "agents/intelligence/peer_compare_agent.py",
                "agents/intelligence/factor_score_agent.py",
                "agents/intelligence/composite_valuation_agent.py",
                "agents/intelligence/ask_adam_agent.py",
                "agents/intelligence/target_price_agent.py",
                "agents/intelligence/verdict_orchestrator_agent.py",
                "agents/intelligence/theme_match_agent.py"
            ],
            
            # Forecasting Agents
            "intelligence/forecasting": [
                "agents/forecast/price_forecast_agent.py",
                "agents/forecast/earnings_forecast_agent.py"
            ],
            
            # Corporate Events Agents
            "events_corporate": [
                "agents/event/corporate_action_agent.py",
                "agents/event/corporate_actions_agent.py",
                "agents/event/earnings_surprise_agent.py",
                "agents/event/earnings_date_agent.py",
                "agents/event/earnings_calendar_agent.py",
                "agents/event/insider_trade_agent.py",
                "agents/event/dividend_declaration_agent.py",
                "agents/event/share_buyback_agent.py"
            ],
            
            # ESG Analysis Agents
            "esg_analysis": [
                "agents/esg/social_agent.py",
                "agents/esg/management_track_record_agent.py",
                "agents/esg/governance_agent.py",
                "agents/esg/esg_score_agent.py",
                "agents/esg/environmental_agent.py",
                "agents/esg/composite_esg_agent.py",
                "agents/management/management_track_record_agent.py"
            ],
            
            # Macro Economic Agents
            "macro_economic": [
                "agents/macro/interest_rate_agent.py",
                "agents/macro/inflation_agent.py",
                "agents/macro/gdp_growth_agent.py"
            ],
            
            # NLP Processing Agents
            "nlp_processing": [
                "agents/nlp/nlp_topic_agent.py",
                "agents/nlp/nlp_summary_agent.py"
            ]
        }
    
    def migrate_all_agents(self):
        """Execute comprehensive agent migration"""
        logger.info("🚀 Starting comprehensive agent migration...")
        
        total_migrated = 0
        total_errors = 0
        migration_summary = {}
        
        for category, agent_files in self.agent_categories.items():
            category_migrated = 0
            category_errors = 0
            
            logger.info(f"📁 Migrating {category} agents...")
            
            # Create category directory
            target_dir = self.backend_path / "agents" / category
            target_dir.mkdir(parents=True, exist_ok=True)
            
            for agent_file in agent_files:
                source_path = self.backend_path / agent_file
                target_path = target_dir / Path(agent_file).name
                
                try:
                    if source_path.exists():
                        # Copy file to new location
                        shutil.copy2(source_path, target_path)
                        logger.success(f"✅ Migrated: {agent_file} -> {category}")
                        category_migrated += 1
                        total_migrated += 1
                    else:
                        logger.warning(f"⚠️ File not found: {agent_file}")
                        
                except Exception as e:
                    logger.error(f"❌ Failed to migrate {agent_file}: {e}")
                    category_errors += 1
                    total_errors += 1
            
            migration_summary[category] = {
                "migrated": category_migrated,
                "errors": category_errors
            }
            
            # Create category __init__.py
            self._create_category_init(target_dir, category)
        
        # Print migration summary
        self._print_migration_summary(migration_summary, total_migrated, total_errors)
        
        # Create agent inventory
        self._create_agent_inventory()
        
        logger.success(f"✅ Migration completed! {total_migrated} agents migrated, {total_errors} errors")
    
    def _create_category_init(self, category_dir: Path, category_name: str):
        """Create __init__.py file for each category"""
        try:
            init_file = category_dir / "__init__.py"
            
            # Generate import statements for all agents in category
            agent_files = [f for f in category_dir.glob("*_agent.py")]
            imports = []
            all_exports = []
            
            for agent_file in agent_files:
                module_name = agent_file.stem
                class_name = self._get_class_name_from_file(module_name)
                imports.append(f"# from .{module_name} import {class_name}")
                all_exports.append(f'    "{class_name}"')
            
            content = f'''"""
{category_name.replace('_', ' ').title()} Agents
{('=' * (len(category_name) + 7))}

{category_name.replace('_', ' ').title()} agents for the Zion Market Analysis Platform.
"""

# Import all agents in this category
{chr(10).join(imports)}

__all__ = [
{chr(10).join(all_exports)}
]
'''
            
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write(content)
                
            logger.debug(f"📝 Created __init__.py for {category_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create __init__.py for {category_name}: {e}")
    
    def _get_class_name_from_file(self, module_name: str) -> str:
        """Generate likely class name from module name"""
        # Convert snake_case to PascalCase
        parts = module_name.replace('_agent', '').split('_')
        return ''.join(word.capitalize() for word in parts) + 'Agent'
    
    def _print_migration_summary(self, summary: Dict, total_migrated: int, total_errors: int):
        """Print detailed migration summary"""
        logger.info("📊 MIGRATION SUMMARY")
        logger.info("=" * 50)
        
        for category, stats in summary.items():
            status = "✅" if stats["errors"] == 0 else "⚠️"
            logger.info(f"{status} {category}: {stats['migrated']} migrated, {stats['errors']} errors")
        
        logger.info("=" * 50)
        logger.info(f"📈 TOTAL: {total_migrated} agents migrated")
        logger.info(f"❌ ERRORS: {total_errors} failed migrations")
        logger.info(f"📊 SUCCESS RATE: {(total_migrated / (total_migrated + total_errors)) * 100:.1f}%")
    
    def _create_agent_inventory(self):
        """Create comprehensive agent inventory"""
        try:
            inventory_content = "# Zion Platform Agent Inventory\\n"
            inventory_content += f"**Generated: {self._get_timestamp()}**\\n\\n"
            
            total_agents = 0
            
            for category, agent_files in self.agent_categories.items():
                category_dir = self.backend_path / "agents" / category
                actual_files = list(category_dir.glob("*_agent.py")) if category_dir.exists() else []
                
                inventory_content += f"## {category.replace('_', ' ').title()}\\n"
                inventory_content += f"**Location**: `backend/agents/{category}/`\\n"
                inventory_content += f"**Count**: {len(actual_files)} agents\\n\\n"
                
                for agent_file in sorted(actual_files):
                    class_name = self._get_class_name_from_file(agent_file.stem)
                    inventory_content += f"- **{class_name}** (`{agent_file.name}`)\\n"
                
                inventory_content += "\\n"
                total_agents += len(actual_files)
            
            inventory_content += f"## Summary\\n"
            inventory_content += f"**Total Agents**: {total_agents}\\n"
            inventory_content += f"**Categories**: {len(self.agent_categories)}\\n"
            
            # Write inventory file
            inventory_file = self.base_path / "AGENT_INVENTORY.md"
            with open(inventory_file, 'w', encoding='utf-8') as f:
                f.write(inventory_content)
            
            logger.success(f"📋 Created agent inventory: {inventory_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create agent inventory: {e}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    """Run comprehensive agent migration"""
    migrator = ComprehensiveAgentMigrator()
    migrator.migrate_all_agents()

if __name__ == "__main__":
    main()
