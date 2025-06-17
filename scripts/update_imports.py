"""
Import Statement Update Script
=============================

Updates all import statements to reflect the new directory structure.
"""

import os
import re
from pathlib import Path
from typing import Dict, List
from loguru import logger

class ImportUpdater:
    """Updates import statements for the new directory structure"""
    
    def __init__(self, base_path: str = "d:/Zion"):
        self.base_path = Path(base_path)
        self.backend_path = self.base_path / "backend"
        
        # Define import mapping rules
        self.import_mappings = {
            # Stealth agents -> Web scrapers
            r"from backend\.agents\.stealth": "from backend.agents.data_collectors.web_scrapers",
            r"from \.\.agents\.stealth": "from ..agents.data_collectors.web_scrapers",
            r"from agents\.stealth": "from agents.data_collectors.web_scrapers",
            r"import backend\.agents\.stealth": "import backend.agents.data_collectors.web_scrapers",
            
            # Technical analysis
            r"from backend\.agents\.technical": "from backend.agents.analysis.technical",
            r"from \.\.agents\.technical": "from ..agents.analysis.technical",
            r"from agents\.technical": "from agents.analysis.technical",
            
            # Valuation -> Fundamental
            r"from backend\.agents\.valuation": "from backend.agents.analysis.fundamental",
            r"from \.\.agents\.valuation": "from ..agents.analysis.fundamental",
            r"from agents\.valuation": "from agents.analysis.fundamental",
            
            # Financial -> Fundamental
            r"from backend\.agents\.financial": "from backend.agents.analysis.fundamental",
            r"from \.\.agents\.financial": "from ..agents.analysis.fundamental",
            r"from agents\.financial": "from agents.analysis.fundamental",
            
            # Intelligence agents
            r"from backend\.agents\.intelligence": "from backend.agents.intelligence.ai_analysis",
            r"from \.\.agents\.intelligence": "from ..agents.intelligence.ai_analysis",
            
            # NLP agents
            r"from backend\.agents\.nlp": "from backend.agents.intelligence.nlp_processing",
            r"from \.\.agents\.nlp": "from ..agents.intelligence.nlp_processing",
            
            # ML agents
            r"from backend\.agents\.ml": "from backend.agents.intelligence.machine_learning",
            r"from \.\.agents\.ml": "from ..agents.intelligence.machine_learning",
            
            # Risk management
            r"from backend\.agents\.risk": "from backend.agents.risk_management.portfolio",
            r"from \.\.agents\.risk": "from ..agents.risk_management.portfolio",
            
            # Sentiment analysis
            r"from backend\.agents\.sentiment": "from backend.agents.analysis.sentiment",
            r"from \.\.agents\.sentiment": "from ..agents.analysis.sentiment",
            
            # ESG analysis
            r"from backend\.agents\.esg": "from backend.agents.analysis.esg",
            r"from \.\.agents\.esg": "from ..agents.analysis.esg",
            
            # Events
            r"from backend\.agents\.events": "from backend.agents.analysis.events",
            r"from \.\.agents\.events": "from ..agents.analysis.events",
            
            # Macro economic
            r"from backend\.agents\.macro": "from backend.agents.analysis.macro_economic",
            r"from \.\.agents\.macro": "from ..agents.analysis.macro_economic",
            
            # Core agents
            r"from backend\.agents\.base": "from backend.agents.core",
            r"from \.\.agents\.base": "from ..agents.core",
            
            # Orchestrator
            r"from backend\.orchestrator": "from backend.orchestrator.master_coordinator",
            r"from \.\.orchestrator": "from ..orchestrator.master_coordinator",
            
            # Services
            r"from backend\.services\.continuous_data_service": "from backend.services.enhanced_websocket_service",
            r"from \.\.services\.continuous_data_service": "from ..services.enhanced_websocket_service"
        }
        
        # Specific agent imports
        self.agent_specific_mappings = {
            # MoneyControl agent
            r"from.*moneycontrol_agent import": "from backend.agents.data_collectors.web_scrapers.moneycontrol_agent import",
            r"from.*trendlyne_agent import": "from backend.agents.data_collectors.web_scrapers.trendlyne_agent import",
            r"from.*stockedge_agent import": "from backend.agents.data_collectors.web_scrapers.stockedge_agent import",
            r"from.*screener_agent import": "from backend.agents.data_collectors.web_scrapers.screener_agent import",
            
            # Base agent imports
            r"from.*base_agent import": "from backend.agents.core.base_agent import",
            r"from.*BaseAgent": "from backend.agents.core.base_agent import EnhancedBaseAgent as BaseAgent",
        }
    
    def update_all_imports(self):
        """Update imports in all Python files"""
        logger.info("🔄 Starting import statement updates...")
        
        # Find all Python files
        python_files = list(self.backend_path.rglob("*.py"))
        updated_count = 0
        
        for file_path in python_files:
            if self._update_file_imports(file_path):
                updated_count += 1
        
        logger.success(f"✅ Updated imports in {updated_count} files")
        
        # Update main app.py
        app_file = self.base_path / "app.py"
        if app_file.exists():
            self._update_app_imports(app_file)
    
    def _update_file_imports(self, file_path: Path) -> bool:
        """Update imports in a single file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Apply general import mappings
            for old_pattern, new_pattern in self.import_mappings.items():
                content = re.sub(old_pattern, new_pattern, content)
            
            # Apply agent-specific mappings
            for old_pattern, new_pattern in self.agent_specific_mappings.items():
                content = re.sub(old_pattern, new_pattern, content)
            
            # Write back if changed
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.debug(f"📝 Updated imports: {file_path.relative_to(self.base_path)}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to update {file_path}: {e}")
            return False
    
    def _update_app_imports(self, app_file: Path):
        """Update imports in main app.py"""
        try:
            with open(app_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Specific updates for app.py
            app_updates = {
                r"from backend\.agents\.stealth": "from backend.agents.data_collectors.web_scrapers",
                r"from backend\.orchestrator": "from backend.orchestrator.master_coordinator",
                r"from backend\.services\.continuous_data_service": "from backend.services.enhanced_websocket_service",
                r"from backend\.agents\.background_manager": "from backend.orchestrator.master_coordinator",
                r"BackgroundManager": "MasterCoordinator",
                r"background_manager": "master_coordinator"
            }
            
            for old_pattern, new_pattern in app_updates.items():
                content = re.sub(old_pattern, new_pattern, content)
            
            with open(app_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.success("✅ Updated app.py imports")
            
        except Exception as e:
            logger.error(f"❌ Failed to update app.py: {e}")
    
    def create_new_init_files(self):
        """Create __init__.py files for new directory structure"""
        logger.info("📝 Creating __init__.py files...")
        
        init_files = [
            # Analysis categories
            "backend/agents/analysis/__init__.py",
            "backend/agents/analysis/technical/__init__.py",
            "backend/agents/analysis/fundamental/__init__.py",
            "backend/agents/analysis/sentiment/__init__.py",
            "backend/agents/analysis/macro_economic/__init__.py",
            "backend/agents/analysis/esg/__init__.py",
            "backend/agents/analysis/events/__init__.py",
            "backend/agents/analysis/market_analysis/__init__.py",
            
            # Intelligence categories
            "backend/agents/intelligence/__init__.py",
            "backend/agents/intelligence/ai_analysis/__init__.py",
            "backend/agents/intelligence/nlp_processing/__init__.py",
            "backend/agents/intelligence/machine_learning/__init__.py",
            "backend/agents/intelligence/forecasting/__init__.py",
            
            # Execution and risk
            "backend/agents/execution/__init__.py",
            "backend/agents/execution/automation/__init__.py",
            "backend/agents/risk_management/__init__.py",
            "backend/agents/risk_management/portfolio/__init__.py",
            
            # Data processing
            "backend/agents/data_processors/__init__.py",
            "backend/agents/data_validators/__init__.py",
            
            # API providers
            "backend/agents/data_collectors/api_providers/__init__.py"
        ]
        
        for init_path in init_files:
            full_path = self.base_path / init_path
            if not full_path.exists():
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text('"""Agent module"""', encoding='utf-8')
                logger.debug(f"📝 Created: {init_path}")
        
        logger.success("✅ Created all __init__.py files")
    
    def verify_imports(self):
        """Verify that all imports are working"""
        logger.info("🔍 Verifying import statements...")
        
        # Test key imports
        test_imports = [
            "from backend.agents.core.base_agent import EnhancedBaseAgent",
            "from backend.orchestrator.master_coordinator import MasterCoordinator",
            "from backend.data_pipeline.enhanced_pipeline import EnhancedDataPipeline",
            "from backend.services.enhanced_websocket_service import EnhancedWebSocketService"
        ]
        
        for import_statement in test_imports:
            try:
                exec(import_statement)
                logger.success(f"✅ Import working: {import_statement}")
            except Exception as e:
                logger.error(f"❌ Import failed: {import_statement} - {e}")

def main():
    """Run the import updater"""
    updater = ImportUpdater()
    
    # Step 1: Create __init__.py files
    updater.create_new_init_files()
    
    # Step 2: Update all import statements
    updater.update_all_imports()
    
    # Step 3: Verify imports (optional - might fail in script context)
    # updater.verify_imports()
    
    logger.success("🎯 Import update completed!")

if __name__ == "__main__":
    main()
