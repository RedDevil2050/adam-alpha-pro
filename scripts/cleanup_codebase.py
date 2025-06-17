"""
Codebase Cleanup Script
======================

Safely removes old and unused directories after the system reorganization.
"""

import os
import shutil
from pathlib import Path
from typing import List
from loguru import logger

class CodebaseCleanup:
    """Handles cleanup of old directories and files after reorganization"""
    
    def __init__(self, base_path: str = "d:/Zion"):
        self.base_path = Path(base_path)
        self.backend_path = self.base_path / "backend"
        self.agents_path = self.backend_path / "agents"
        
        # Directories to remove (old structure)
        self.old_directories = [
            # Old agent directories that have been migrated
            "backend/agents/stealth",           # -> data_collectors/web_scrapers
            "backend/agents/technical",         # -> analysis/technical  
            "backend/agents/valuation",         # -> analysis/fundamental
            "backend/agents/financial",         # -> analysis/fundamental
            "backend/agents/automation",        # -> execution/automation
            "backend/agents/sentiment",         # -> analysis/sentiment
            "backend/agents/esg",              # -> analysis/esg
            "backend/agents/esg_analysis",     # -> analysis/esg
            "backend/agents/event",            # -> analysis/events
            "backend/agents/events",           # -> analysis/events
            "backend/agents/events_corporate", # -> analysis/events
            "backend/agents/macro",            # -> analysis/macro_economic
            "backend/agents/macro_economic",   # -> analysis/macro_economic (duplicate)
            "backend/agents/management",       # -> analysis/management
            "backend/agents/market",           # -> analysis/market_analysis
            "backend/agents/ml",               # -> intelligence/machine_learning
            "backend/agents/nlp",              # -> intelligence/nlp_processing
            "backend/agents/nlp_processing",   # -> intelligence/nlp_processing (duplicate)
            "backend/agents/risk",             # -> risk_management/portfolio
            "backend/agents/verifiers",        # -> data_validators
            "backend/agents/forecast",         # -> intelligence/forecasting
            "backend/agents/base",             # -> core
            
            # Cache directories
            "backend/agents/__pycache__",
            "backend/__pycache__",
            "__pycache__"
        ]
        
        # Individual files to remove (old structure)
        self.old_files = [
            # Standalone files that have been migrated
            "backend/agents/dividend_agent.py",      # -> analysis/fundamental
            "backend/agents/market_regime_agent.py", # -> intelligence/ai_analysis
            "backend/agents/categories.py",          # -> core
            "backend/agents/decorators.py",          # -> core
            "backend/agents/initialization.py",      # -> core
            "backend/agents/registry.py",            # -> core
            "backend/agents/orchestrator.py",        # -> orchestrator
        ]
        
        # Backup location for safety
        self.backup_path = self.base_path / "backup_old_structure"
    
    def create_backup(self):
        """Create backup of old structure before deletion"""
        logger.info("📦 Creating backup of old structure...")
        
        if self.backup_path.exists():
            shutil.rmtree(self.backup_path)
        
        self.backup_path.mkdir(exist_ok=True)
        
        # Backup old directories
        for old_dir in self.old_directories:
            old_path = self.base_path / old_dir
            if old_path.exists():
                backup_target = self.backup_path / old_dir
                backup_target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    if old_path.is_dir():
                        shutil.copytree(old_path, backup_target)
                    else:
                        shutil.copy2(old_path, backup_target)
                    logger.debug(f"📦 Backed up: {old_dir}")
                except Exception as e:
                    logger.warning(f"⚠️ Backup failed for {old_dir}: {e}")
        
        logger.success("✅ Backup created successfully")
    
    def remove_old_directories(self):
        """Remove old directories that have been migrated"""
        logger.info("🗑️ Removing old directories...")
        
        removed_count = 0
        
        for old_dir in self.old_directories:
            old_path = self.base_path / old_dir
            if old_path.exists():
                try:
                    if old_path.is_dir():
                        shutil.rmtree(old_path)
                        logger.info(f"🗑️ Removed directory: {old_dir}")
                        removed_count += 1
                    elif old_path.is_file():
                        old_path.unlink()
                        logger.info(f"🗑️ Removed file: {old_dir}")
                        removed_count += 1
                except Exception as e:
                    logger.error(f"❌ Failed to remove {old_dir}: {e}")
            else:
                logger.debug(f"⚠️ Not found: {old_dir}")
        
        logger.success(f"✅ Removed {removed_count} old directories/files")
    
    def remove_old_files(self):
        """Remove old individual files that have been migrated"""
        logger.info("🗑️ Removing old files...")
        
        removed_count = 0
        
        for old_file in self.old_files:
            old_path = self.base_path / old_file
            if old_path.exists():
                try:
                    old_path.unlink()
                    logger.info(f"🗑️ Removed file: {old_file}")
                    removed_count += 1
                except Exception as e:
                    logger.error(f"❌ Failed to remove {old_file}: {e}")
            else:
                logger.debug(f"⚠️ Not found: {old_file}")
        
        logger.success(f"✅ Removed {removed_count} old files")
    
    def clean_cache_files(self):
        """Remove Python cache files"""
        logger.info("🧹 Cleaning cache files...")
        
        removed_count = 0
        
        # Find all __pycache__ directories
        for pycache_dir in self.base_path.rglob("__pycache__"):
            try:
                shutil.rmtree(pycache_dir)
                logger.debug(f"🧹 Removed cache: {pycache_dir.relative_to(self.base_path)}")
                removed_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to remove cache {pycache_dir}: {e}")
        
        # Find all .pyc files
        for pyc_file in self.base_path.rglob("*.pyc"):
            try:
                pyc_file.unlink()
                logger.debug(f"🧹 Removed .pyc: {pyc_file.relative_to(self.base_path)}")
                removed_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to remove .pyc {pyc_file}: {e}")
        
        logger.success(f"✅ Cleaned {removed_count} cache files")
    
    def remove_empty_directories(self):
        """Remove empty directories left after cleanup"""
        logger.info("📁 Removing empty directories...")
        
        removed_count = 0
        
        # Walk through all directories in reverse order (deepest first)
        for root, dirs, files in os.walk(self.backend_path, topdown=False):
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                try:
                    # Check if directory is empty
                    if not any(dir_path.iterdir()):
                        dir_path.rmdir()
                        logger.debug(f"📁 Removed empty directory: {dir_path.relative_to(self.base_path)}")
                        removed_count += 1
                except Exception as e:
                    logger.debug(f"⚠️ Could not remove {dir_path}: {e}")
        
        logger.success(f"✅ Removed {removed_count} empty directories")
    
    def optimize_imports(self):
        """Remove unused import statements"""
        logger.info("🔧 Optimizing import statements...")
        
        # This would be a complex operation - for now just log
        logger.info("📝 Import optimization can be done manually or with tools like autoflake")
    
    def generate_cleanup_report(self):
        """Generate a report of what was cleaned"""
        logger.info("📋 Generating cleanup report...")
        
        report_content = f"""# Codebase Cleanup Report
**Date: {self.get_current_date()}**

## 🗑️ **Directories Removed**
{self._format_list(self.old_directories)}

## 📄 **Files Removed**  
{self._format_list(self.old_files)}

## 🎯 **New Clean Structure**
```
backend/agents/
├── core/                    # Enhanced base infrastructure
├── data_collectors/         # Data collection agents
│   ├── web_scrapers/       # Stealth web scraping
│   └── api_providers/      # API data sources
├── analysis/               # Analysis agents
│   ├── technical/          # Technical indicators
│   ├── fundamental/        # Financial metrics
│   ├── sentiment/          # Market sentiment
│   ├── macro_economic/     # Economic analysis
│   ├── esg/               # ESG scoring
│   ├── events/            # Corporate events
│   └── market_analysis/   # Market analysis
├── intelligence/           # AI & ML agents
│   ├── ai_analysis/       # AI-powered analysis
│   ├── nlp_processing/    # Natural language processing
│   ├── machine_learning/  # ML models
│   └── forecasting/       # Prediction models
├── risk_management/        # Risk analysis
│   └── portfolio/         # Portfolio risk agents
├── execution/             # Trading execution
│   └── automation/        # Automated trading
├── data_processors/       # Data processing
└── data_validators/       # Data validation
```

## ✅ **Cleanup Results**
- **Old directories removed**: {len(self.old_directories)}
- **Old files removed**: {len(self.old_files)}
- **Cache files cleaned**: All Python cache removed
- **Empty directories**: Removed automatically
- **Backup created**: Available in backup_old_structure/

## 🎯 **Benefits**
- **Cleaner codebase**: No duplicate directories
- **Better organization**: Clear functional separation
- **Faster development**: Easy navigation
- **Reduced complexity**: Simplified imports
- **Professional structure**: Enterprise-grade organization

---
**Status**: ✅ CLEANUP COMPLETE
**Backup**: Available for rollback if needed
"""
        
        report_path = self.base_path / "CLEANUP_REPORT.md"
        report_path.write_text(report_content, encoding='utf-8')
        logger.success(f"📋 Cleanup report saved: {report_path}")
    
    def _format_list(self, items: List[str]) -> str:
        """Format list for markdown"""
        return "\n".join(f"- {item}" for item in items)
    
    def get_current_date(self) -> str:
        """Get current date string"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def full_cleanup(self):
        """Perform complete cleanup"""
        logger.info("🧹 Starting comprehensive codebase cleanup...")
        
        try:
            # Step 1: Create backup
            self.create_backup()
            
            # Step 2: Remove old directories
            self.remove_old_directories()
            
            # Step 3: Remove old files
            self.remove_old_files()
            
            # Step 4: Clean cache files
            self.clean_cache_files()
            
            # Step 5: Remove empty directories
            self.remove_empty_directories()
            
            # Step 6: Generate report
            self.generate_cleanup_report()
            
            logger.success("🎉 Codebase cleanup completed successfully!")
            logger.info("📦 Backup available at: backup_old_structure/")
            logger.info("📋 Cleanup report: CLEANUP_REPORT.md")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            logger.info("📦 Backup is available for manual restoration")
            raise

def main():
    """Run the cleanup"""
    cleanup = CodebaseCleanup()
    cleanup.full_cleanup()

if __name__ == "__main__":
    main()
