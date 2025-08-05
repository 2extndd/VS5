#!/usr/bin/env python3
"""
Comprehensive Database Tests
Tests PostgreSQL connection, price types, migrations, and item storage
"""

import sys
import os
import time
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import db
from logger import get_logger

def test_db_connection():
    """Test database connection"""
    print("🔌 Testing database connection...")
    
    try:
        conn, db_type = db.get_db_connection()
        logger = get_logger(__name__)
        
        print(f"✅ Connected to {db_type} database")
        
        if db_type == 'postgresql':
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"📊 PostgreSQL version: {version[0]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_price_migration():
    """Test price type migration"""
    print("\n🔧 Testing price type migration...")
    
    try:
        # Apply the migration
        success = db.apply_migration("migrations/fix_price_type.sql")
        
        if success:
            print("✅ Price migration applied successfully")
            return True
        else:
            print("❌ Price migration failed")
            return False
            
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False

def test_table_schema():
    """Test table schema and column types"""
    print("\n📋 Testing table schema...")
    
    try:
        conn, db_type = db.get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgresql':
            # Check items table schema
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'items' 
                ORDER BY ordinal_position;
            """)
            
            columns = cursor.fetchall()
            print("📊 Items table schema:")
            for col_name, data_type in columns:
                print(f"   {col_name}: {data_type}")
                
            # Check if price is DECIMAL
            price_type = next((dt for cn, dt in columns if cn == 'price'), None)
            if price_type and 'numeric' in price_type.lower():
                print("✅ Price column is DECIMAL/NUMERIC type")
            else:
                print(f"❌ Price column type is {price_type} (should be DECIMAL)")
                return False
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Schema check failed: {e}")
        return False

def test_decimal_prices():
    """Test adding items with decimal prices"""
    print("\n💰 Testing decimal price storage...")
    
    test_items = [
        ("test_item_1", "Test Item 1", 15.50, "EUR"),
        ("test_item_2", "Test Item 2", 29.99, "EUR"), 
        ("test_item_3", "Test Item 3", 100.0, "USD"),
        ("test_item_4", "Test Item 4", 5.75, "EUR"),
    ]
    
    # First ensure we have a test query
    try:
        test_query = "https://www.vinted.de/catalog?order=newest_first&test=true"
        
        # Add test query if it doesn't exist
        if not db.is_query_in_db(test_query):
            db.add_query_to_db(test_query, "Test Query")
            
        # Get query ID
        queries = db.get_queries()
        test_query_id = None
        for query in queries:
            if "test=true" in query[1]:  # query[1] is the query URL
                test_query_id = query[0]  # query[0] is the ID
                break
                
        if not test_query_id:
            print("❌ Could not create/find test query")
            return False
            
        print(f"📝 Using test query ID: {test_query_id}")
        
        # Test adding items with decimal prices
        for item_id, title, price, currency in test_items:
            timestamp = int(time.time())
            photo_url = f"https://example.com/{item_id}.jpg"
            
            print(f"💾 Adding item: {title} - {price} {currency}")
            
            try:
                db.add_item_to_db(
                    id=item_id,
                    title=title, 
                    query_id=test_query_id,
                    price=price,
                    timestamp=timestamp,
                    photo_url=photo_url,
                    currency=currency
                )
                print(f"   ✅ Successfully added {item_id}")
                
            except Exception as e:
                print(f"   ❌ Failed to add {item_id}: {e}")
                return False
                
        print("✅ All decimal prices stored successfully")
        return True
        
    except Exception as e:
        print(f"❌ Decimal price test failed: {e}")
        return False

def test_item_retrieval():
    """Test retrieving items from database"""
    print("\n📥 Testing item retrieval...")
    
    try:
        # Get all items
        items = db.get_items(limit=10)
        
        if not items:
            print("⚠️  No items found in database")
            return True  # Not an error if no items
            
        print(f"📊 Found {len(items)} items:")
        
        for item in items[:5]:  # Show first 5 items
            # item format: (item_id, title, price, currency, timestamp, query, photo_url)
            item_id, title, price, currency, timestamp, query, photo_url = item
            print(f"   🛍️  {item_id}: {title} - {price} {currency}")
            
            # Verify price is a valid number
            try:
                float(price)
                print(f"      ✅ Price {price} is valid decimal")
            except (ValueError, TypeError):
                print(f"      ❌ Price {price} is invalid")
                return False
                
        print("✅ Item retrieval successful")
        return True
        
    except Exception as e:
        print(f"❌ Item retrieval failed: {e}")
        return False

def test_item_count():
    """Test item count functionality"""
    print("\n🔢 Testing item count...")
    
    try:
        count = db.get_total_items_count()
        print(f"📊 Total items in database: {count}")
        
        if isinstance(count, int) and count >= 0:
            print("✅ Item count is valid")
            return True
        else:
            print(f"❌ Invalid item count: {count}")
            return False
            
    except Exception as e:
        print(f"❌ Item count test failed: {e}")
        return False

def cleanup_test_data():
    """Clean up test data"""
    print("\n🧹 Cleaning up test data...")
    
    try:
        conn, db_type = db.get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgresql':
            # Delete test items
            cursor.execute("DELETE FROM items WHERE item LIKE 'test_item_%'")
            deleted_items = cursor.rowcount
            
            # Delete test query
            cursor.execute("DELETE FROM queries WHERE query LIKE '%test=true%'")
            deleted_queries = cursor.rowcount
            
            conn.commit()
            print(f"🗑️  Deleted {deleted_items} test items and {deleted_queries} test queries")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False

def main():
    """Run all database tests"""
    print("🧪 КОМПЛЕКСНЫЙ ТЕСТ БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    tests = [
        ("Database Connection", test_db_connection),
        ("Price Migration", test_price_migration), 
        ("Table Schema", test_table_schema),
        ("Decimal Prices", test_decimal_prices),
        ("Item Retrieval", test_item_retrieval),
        ("Item Count", test_item_count),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
                failed += 1
        except Exception as e:
            print(f"💥 {test_name} CRASHED: {e}")
            failed += 1
    
    # Cleanup
    print(f"\n{'='*20} Cleanup {'='*20}")
    cleanup_test_data()
    
    # Results
    print(f"\n🏁 РЕЗУЛЬТАТЫ ТЕСТОВ")
    print("=" * 50)
    print(f"✅ Прошли: {passed}")
    print(f"❌ Провалились: {failed}")
    print(f"📊 Всего: {passed + failed}")
    
    if failed == 0:
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        return True
    else:
        print("💥 ЕСТЬ ПРОВАЛЕННЫЕ ТЕСТЫ!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)