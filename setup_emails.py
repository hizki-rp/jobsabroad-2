#!/usr/bin/env python
"""
Simple script to set up the email system
Run this script to create the necessary database tables and default templates
"""

import os
import sys
import django
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'university_api.settings')
django.setup()

from django.db import connection
from emails.services import EmailService

def setup_emails():
    """Set up the email system"""
    print("Setting up email system...")
    
    try:
        # Create tables using raw SQL
        with connection.cursor() as cursor:
            # Read and execute the SQL setup script
            sql_file = backend_dir / 'emails' / 'setup_emails.sql'
            if sql_file.exists():
                with open(sql_file, 'r') as f:
                    sql_content = f.read()
                
                # Split by semicolon and execute each statement
                statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
                for statement in statements:
                    if statement:
                        cursor.execute(statement)
                
                print("✅ Database tables created successfully")
            else:
                print("❌ SQL setup file not found")
                return False
        
        # Create default templates
        print("Creating default templates...")
        EmailService.create_default_templates()
        print("✅ Default templates created")
        
        print("🎉 Email system setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error setting up email system: {str(e)}")
        return False

if __name__ == "__main__":
    success = setup_emails()
    sys.exit(0 if success else 1)




