#!/usr/bin/env python3
"""
Migration script for adding found_at column to items table
"""
import db
from logger import get_logger

logger = get_logger(__name__)

def run_migration():
    """Run database migration to add found_at field"""
    try:
        conn, db_type = db.get_db_connection()
        cursor = conn.cursor()
        
        logger.info("Starting migration: Add found_at column")
        logger.info(f"Database type: {db_type}")
        
        # Check if column already exists
        if db_type == 'postgresql':
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='items' AND column_name='found_at'
            """)
        else:
            cursor.execute("PRAGMA table_info(items)")
            columns = [row[1] for row in cursor.fetchall()]
            found_at_exists = 'found_at' in columns
        
        if db_type == 'postgresql':
            result = cursor.fetchone()
            found_at_exists = result is not None
        
        if found_at_exists:
            logger.info("✓ Column 'found_at' already exists. Migration not needed.")
            return True
        
        # Add found_at column
        logger.info("Adding found_at column...")
        cursor.execute("ALTER TABLE items ADD COLUMN found_at NUMERIC")
        
        # Update existing items
        logger.info("Updating existing items with found_at = timestamp...")
        cursor.execute("UPDATE items SET found_at = timestamp WHERE found_at IS NULL")
        
        # Add indexes
        logger.info("Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_timestamp ON items(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_query_id ON items(query_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_found_at ON items(found_at)")
        
        conn.commit()
        logger.info("✓ Migration completed successfully!")
        
        # Verify
        if db_type == 'postgresql':
            cursor.execute("SELECT COUNT(*) FROM items WHERE found_at IS NOT NULL")
        else:
            cursor.execute("SELECT COUNT(*) FROM items WHERE found_at IS NOT NULL")
        
        count = cursor.fetchone()[0]
        logger.info(f"✓ {count} items have found_at timestamp")
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("  Database Migration: Add found_at column")
    print("=" * 60)
    
    success = run_migration()
    
    if success:
        print("\n✓ Migration completed successfully!")
    else:
        print("\n✗ Migration failed. Check logs for details.")
        exit(1)

