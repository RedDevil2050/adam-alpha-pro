#!/usr/bin/env python3
"""
Cleanup Script for Old Stealth Test Files
=========================================

This script backs up and optionally removes the old individual test files
that have been consolidated into unified_stealth_test.py
"""

import os
import shutil
from datetime import datetime

def backup_and_cleanup():
    """Backup old test files and optionally remove them"""
    
    # Files to backup/cleanup
    old_test_files = [
        'test_all_stealth_agents.py',
        'test_stealth_agents_simple.py', 
        'test_stealth_agent.py',
        'test_quad_channel_stealth.py',
        'test_working_stealth_agents.py',
        'test_503_handling.py',
        'test_improved_agents.py',
        'monitor_stealth_health.py'
    ]
    
    # Create backup directory
    backup_dir = f"backup_stealth_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"🗂️  Creating backup directory: {backup_dir}")
    os.makedirs(backup_dir, exist_ok=True)
    
    backed_up_files = []
    missing_files = []
    
    # Backup existing files
    for filename in old_test_files:
        if os.path.exists(filename):
            try:
                shutil.copy2(filename, backup_dir)
                backed_up_files.append(filename)
                print(f"✅ Backed up: {filename}")
            except Exception as e:
                print(f"❌ Failed to backup {filename}: {e}")
        else:
            missing_files.append(filename)
            print(f"⚠️  File not found: {filename}")
    
    print(f"\n📊 Backup Summary:")
    print(f"   - Files backed up: {len(backed_up_files)}")
    print(f"   - Files missing: {len(missing_files)}")
    print(f"   - Backup location: ./{backup_dir}")
    
    # Ask user if they want to remove original files
    if backed_up_files:
        print(f"\n🗑️  The following files have been backed up:")
        for f in backed_up_files:
            print(f"   - {f}")
        
        choice = input("\nDo you want to remove the original files? (y/N): ").strip().lower()
        
        if choice == 'y':
            removed_files = []
            for filename in backed_up_files:
                try:
                    os.remove(filename)
                    removed_files.append(filename)
                    print(f"🗑️  Removed: {filename}")
                except Exception as e:
                    print(f"❌ Failed to remove {filename}: {e}")
            
            print(f"\n✅ Cleanup completed! Removed {len(removed_files)} files.")
            print(f"   Original files are safely backed up in: {backup_dir}")
        else:
            print(f"\n✅ Files preserved. Backup available in: {backup_dir}")
    
    # Create a README in backup directory
    readme_content = f"""# Stealth Test Files Backup

This directory contains backup copies of individual stealth agent test files 
that were consolidated into `unified_stealth_test.py`.

## Backup Date
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Consolidated Features
All functionality from these individual files has been integrated into:
`unified_stealth_test.py`

## Files Backed Up
{chr(10).join(f'- {f}' for f in backed_up_files)}

## Missing Files  
{chr(10).join(f'- {f}' for f in missing_files) if missing_files else 'None'}

## Usage
To use the new consolidated test suite:

```bash
# Quick test (default)
python unified_stealth_test.py

# Comprehensive test
python unified_stealth_test.py --mode comprehensive

# Health monitoring
python unified_stealth_test.py --mode health

# Error handling test
python unified_stealth_test.py --mode errors

# Custom symbols
python unified_stealth_test.py --mode quick --symbols RELIANCE TCS INFY
```

## Restoration
If you need to restore any of these files, simply copy them back to the main directory.
"""
    
    readme_path = os.path.join(backup_dir, 'README.md')
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    
    print(f"\n📝 Created README.md in backup directory")
    print(f"\n🎉 Consolidation complete! Use 'python unified_stealth_test.py' for all testing needs.")

if __name__ == "__main__":
    backup_and_cleanup()
