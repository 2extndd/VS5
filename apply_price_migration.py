#!/usr/bin/env python3
"""
Script to apply price type migration to existing PostgreSQL database
This fixes the BIGINT -> DECIMAL issue for price fields
"""

import sys
import os

# Add current directory to path to import db module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import db
from logger import get_logger

def main():
    logger = get_logger(__name__)
    
    logger.info("🔧 Starting price type migration...")
    
    # Apply the migration
    success = db.apply_migration("migrations/fix_price_type.sql")
    
    if success:
        logger.info("✅ Price type migration applied successfully!")
        logger.info("🎯 Items should now save properly to database")
    else:
        logger.error("❌ Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()