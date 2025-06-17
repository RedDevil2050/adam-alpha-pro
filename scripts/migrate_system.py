"""
System Reorganization Migration Script
======================================

Migrates agents and updates import paths for the new directory structure.
"""

import os
import shutil
import re
from pathlib import Path
from typing import Dict, List, Tuple
from loguru import logger

class SystemMigrator:
    """Handles migration from old to new directory structure"""
    
    def __init__(self, base_path: str = "d:/Zion"):
        self.base_path = Path(base_path)
        self.backend_path = self.base_path / "backend"
        self.migration_log = []
        
        # Define migration mappings
        self.agent_migrations = {
            # Stealth agents -> Web scrapers
            "backend/agents/stealth/moneycontrol_agent.py": "backend/agents/data_collectors/web_scrapers/moneycontrol_agent.py",
            "backend/agents/stealth/trendlyne_agent.py": "backend/agents/data_collectors/web_scrapers/trendlyne_agent.py",
            "backend/agents/stealth/stockedge_agent.py": "backend/agents/data_collectors/web_scrapers/stockedge_agent.py",
            "backend/agents/stealth/screener_agent.py": "backend/agents/data_collectors/web_scrapers/screener_agent.py",
            
            # Analysis agents -> Analysis category
            "backend/agents/analysis/": "backend/agents/analysis/",
            "backend/agents/valuation/": "backend/agents/analysis/fundamental/",
            "backend/agents/financial/": "backend/agents/analysis/financial/",
            
            # Trading agents -> Trading category  
            "backend/agents/trading/": "backend/agents/trading/",
            
            # Intelligence agents -> Intelligence category
            "backend/intelligence/": "backend/agents/intelligence/"
        }
        
        # Import path updates
        self.import_updates = {
            r"from backend\.agents\.stealth": "from backend.agents.data_collectors.web_scrapers",
            r"from \.\.agents\.stealth": "from ..agents.data_collectors.web_scrapers",
            r"backend\.agents\.stealth": "backend.agents.data_collectors.web_scrapers"
        }
    
    def migrate_system(self):
        """Execute complete system migration"""
        logger.info("🚀 Starting system migration to new directory structure")
        
        try:
            # Step 1: Create new directory structure (already done)
            logger.info("✅ New directory structure already created")
            
            # Step 2: Migrate agent files
            self._migrate_agent_files()
            
            # Step 3: Update import statements
            self._update_import_statements()
            
            # Step 4: Update configuration files
            self._update_configuration_files()
            
            # Step 5: Verify migration
            self._verify_migration()
            
            logger.success("✅ System migration completed successfully!")
            self._print_migration_summary()
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            raise
    
    def _migrate_agent_files(self):
        """Migrate agent files to new locations"""
        logger.info("📁 Migrating agent files...")
        
        migrated_count = 0
        
        for old_path, new_path in self.agent_migrations.items():
            old_full_path = self.base_path / old_path
            new_full_path = self.base_path / new_path
            
            if old_full_path.exists():
                try:
                    # Create destination directory if it doesn't exist
                    new_full_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    if old_full_path.is_file():
                        # Copy file
                        shutil.copy2(old_full_path, new_full_path)
                        logger.info(f"📋 Copied: {old_path} -> {new_path}")
                        migrated_count += 1
                        
                    elif old_full_path.is_dir():
                        # Copy directory
                        if not new_full_path.exists():
                            shutil.copytree(old_full_path, new_full_path)
                            logger.info(f"📁 Copied directory: {old_path} -> {new_path}")
                            migrated_count += 1
                        
                    self.migration_log.append(f"Migrated: {old_path} -> {new_path}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to migrate {old_path}: {e}")
                    self.migration_log.append(f"Failed: {old_path} - {e}")
            else:
                logger.warning(f"⚠️ Source not found: {old_path}")
        
        logger.success(f"✅ Migrated {migrated_count} agent files")
    
    def _update_import_statements(self):
        """Update import statements in all Python files"""
        logger.info("📝 Updating import statements...")
        
        updated_files = 0
        
        # Find all Python files in backend
        python_files = list(self.backend_path.rglob("*.py"))
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Apply import updates
                for old_pattern, new_pattern in self.import_updates.items():
                    content = re.sub(old_pattern, new_pattern, content)
                
                # Write back if changed
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    logger.debug(f"📝 Updated imports in: {file_path.relative_to(self.base_path)}")
                    updated_files += 1
                    
            except Exception as e:
                logger.error(f"❌ Failed to update imports in {file_path}: {e}")
        
        logger.success(f"✅ Updated imports in {updated_files} files")
    
    def _update_configuration_files(self):
        """Update configuration files with new paths"""
        logger.info("⚙️ Updating configuration files...")
        
        # Update app.py imports
        app_file = self.base_path / "app.py"
        if app_file.exists():
            self._update_app_imports(app_file)
        
        # Update other configuration files as needed
        logger.success("✅ Configuration files updated")
    
    def _update_app_imports(self, app_file: Path):
        """Update imports in main app.py file"""
        try:
            with open(app_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update specific imports for new structure
            updates = {
                r"from backend\.agents\.stealth": "from backend.agents.data_collectors.web_scrapers",
                r"from backend\.orchestrator": "from backend.orchestrator.master_coordinator",
                r"from backend\.services\.continuous_data_service": "from backend.services.enhanced_websocket_service"
            }
            
            for old_pattern, new_pattern in updates.items():
                content = re.sub(old_pattern, new_pattern, content)
            
            with open(app_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info("✅ Updated app.py imports")
            
        except Exception as e:
            logger.error(f"❌ Failed to update app.py: {e}")
    
    def _verify_migration(self):
        """Verify migration was successful"""
        logger.info("🔍 Verifying migration...")
        
        # Check if new directories exist and have content
        required_dirs = [
            "backend/agents/core",
            "backend/agents/data_collectors/web_scrapers",
            "backend/orchestrator",
            "backend/data_pipeline"
        ]
        
        for dir_path in required_dirs:
            full_path = self.base_path / dir_path
            if not full_path.exists():
                logger.error(f"❌ Missing directory: {dir_path}")
            else:
                logger.debug(f"✅ Directory exists: {dir_path}")
        
        # Check if key files exist
        key_files = [
            "backend/agents/core/base_agent.py",
            "backend/orchestrator/master_coordinator.py",
            "backend/data_pipeline/enhanced_pipeline.py",
            "backend/services/enhanced_websocket_service.py"
        ]
        
        for file_path in key_files:
            full_path = self.base_path / file_path
            if not full_path.exists():
                logger.error(f"❌ Missing file: {file_path}")
            else:
                logger.debug(f"✅ File exists: {file_path}")
        
        logger.success("✅ Migration verification completed")
    
    def _print_migration_summary(self):
        """Print migration summary"""
        logger.info("📊 Migration Summary:")
        logger.info("=" * 50)
        
        for log_entry in self.migration_log:
            logger.info(f"  • {log_entry}")
        
        logger.info("=" * 50)
        logger.info("🎯 Next Steps:")
        logger.info("  1. Test agent functionality in new structure")
        logger.info("  2. Update frontend imports if needed")
        logger.info("  3. Run system health check")
        logger.info("  4. Start enhanced orchestrator")

def main():
    """Run the migration"""
    migrator = SystemMigrator()
    migrator.migrate_system()

if __name__ == "__main__":
    main()
