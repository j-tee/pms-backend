#!/usr/bin/env python
"""
Test script for database connection and configuration.
Tests PostgreSQL connection and PostGIS extension.

Usage:
    python test-scripts/test_database.py
"""

import os
import sys
import django

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection
from django.conf import settings


def test_database_connection():
    """Test database connection and configuration."""
    
    print('=' * 60)
    print('DATABASE CONNECTION TEST')
    print('=' * 60)
    print()
    
    # Display configuration
    db_config = settings.DATABASES['default']
    print('Current Configuration:')
    print(f'  Engine:   {db_config["ENGINE"]}')
    print(f'  Name:     {db_config["NAME"]}')
    print(f'  User:     {db_config["USER"]}')
    print(f'  Host:     {db_config["HOST"]}')
    print(f'  Port:     {db_config["PORT"]}')
    print()
    
    # Test connection
    print('Testing connection...')
    try:
        with connection.cursor() as cursor:
            # Test basic query
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f'✅ Connected to PostgreSQL')
            print(f'   Version: {version}')
            print()
            
            # Test PostGIS extension
            print('Checking PostGIS extension...')
            cursor.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM pg_extension WHERE extname = 'postgis'
                );
            """)
            has_postgis = cursor.fetchone()[0]
            
            if has_postgis:
                cursor.execute("SELECT PostGIS_Version();")
                postgis_version = cursor.fetchone()[0]
                print(f'✅ PostGIS is installed')
                print(f'   Version: {postgis_version}')
            else:
                print('⚠️  PostGIS is NOT installed')
                print('   Run: CREATE EXTENSION postgis;')
            print()
            
            # List all tables
            print('Tables in database:')
            cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                ORDER BY tablename;
            """)
            tables = cursor.fetchall()
            for table in tables:
                print(f'   - {table[0]}')
            print(f'   Total: {len(tables)} tables')
            print()
            
            # Count users
            try:
                cursor.execute("SELECT COUNT(*) FROM users;")
                user_count = cursor.fetchone()[0]
                print(f'Users in database: {user_count}')
            except Exception as e:
                print(f'⚠️  Could not count users: {e}')
            
    except Exception as e:
        print('❌ ERROR: Database connection failed')
        print()
        print(f'Error details: {str(e)}')
        print()
        print('Common issues:')
        print('  1. Check database credentials in .env.development')
        print('  2. Ensure PostgreSQL server is running')
        print('  3. Verify database exists and user has permissions')
        print('  4. Check firewall/network settings')
        return False
    
    print()
    print('=' * 60)
    print('✅ DATABASE TEST COMPLETED SUCCESSFULLY!')
    print('=' * 60)
    return True


if __name__ == '__main__':
    test_database_connection()
