#!/usr/bin/env python3
"""
Database management and migration system for Media Management Service
"""

import os
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.exc import OperationalError
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database management and migration system"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.migrations_table = 'schema_migrations'
    
    def ensure_migrations_table(self):
        """Ensure migrations tracking table exists"""
        try:
            with self.engine.connect() as conn:
                if 'postgresql' in self.database_url:
                    conn.execute(text(f"""
                        CREATE TABLE IF NOT EXISTS {self.migrations_table} (
                            id SERIAL PRIMARY KEY,
                            version VARCHAR(255) UNIQUE NOT NULL,
                            name VARCHAR(255) NOT NULL,
                            applied_at TIMESTAMP DEFAULT NOW(),
                            checksum VARCHAR(64)
                        )
                    """))
                else:  # SQLite
                    conn.execute(text(f"""
                        CREATE TABLE IF NOT EXISTS {self.migrations_table} (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            version VARCHAR(255) UNIQUE NOT NULL,
                            name VARCHAR(255) NOT NULL,
                            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            checksum VARCHAR(64)
                        )
                    """))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to create migrations table: {e}")
            raise
    
    def get_applied_migrations(self) -> set:
        """Get list of applied migrations"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT version FROM {self.migrations_table}"))
                return {row[0] for row in result}
        except Exception:
            return set()
    
    def apply_migration(self, version: str, name: str, sql: str):
        """Apply a single migration"""
        try:
            with self.engine.connect() as conn:
                # Apply migration SQL
                for statement in sql.split(';'):
                    statement = statement.strip()
                    if statement:
                        conn.execute(text(statement))
                
                # Record migration
                if 'postgresql' in self.database_url:
                    conn.execute(text(f"""
                        INSERT INTO {self.migrations_table} (version, name, applied_at)
                        VALUES (:version, :name, NOW())
                    """), {"version": version, "name": name})
                else:  # SQLite
                    conn.execute(text(f"""
                        INSERT INTO {self.migrations_table} (version, name, applied_at)
                        VALUES (:version, :name, CURRENT_TIMESTAMP)
                    """), {"version": version, "name": name})
                
                conn.commit()
                logger.info(f"Applied migration {version}: {name}")
                
        except Exception as e:
            logger.error(f"Failed to apply migration {version}: {e}")
            raise
    
    def create_initial_schema(self):
        """Create initial database schema"""
        if 'postgresql' in self.database_url:
            initial_sql = """
            -- Initial schema for Media Management Service (PostgreSQL)
            CREATE TABLE IF NOT EXISTS media_files (
                id BIGSERIAL PRIMARY KEY,
                account_id BIGINT NOT NULL,
                original_filename VARCHAR(255) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                file_size BIGINT NOT NULL,
                file_type VARCHAR(50) NOT NULL,
                mime_type VARCHAR(100) NOT NULL,
                file_hash VARCHAR(64) NOT NULL,
                metadata JSONB,
                is_active BOOLEAN DEFAULT TRUE,
                cleanup_status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            
            CREATE TABLE IF NOT EXISTS file_validation_logs (
                id BIGSERIAL PRIMARY KEY,
                media_file_id BIGINT REFERENCES media_files(id),
                validation_type VARCHAR(50) NOT NULL,
                is_valid BOOLEAN NOT NULL,
                validation_details JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            
            CREATE TABLE IF NOT EXISTS file_cleanup_logs (
                id BIGSERIAL PRIMARY KEY,
                media_file_id BIGINT REFERENCES media_files(id),
                cleanup_type VARCHAR(50) NOT NULL,
                success BOOLEAN NOT NULL,
                file_size_freed BIGINT DEFAULT 0,
                cleanup_details JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            
            -- Indexes
            CREATE INDEX IF NOT EXISTS idx_media_files_account_id ON media_files(account_id);
            CREATE INDEX IF NOT EXISTS idx_media_files_file_hash ON media_files(file_hash);
            CREATE INDEX IF NOT EXISTS idx_media_files_is_active ON media_files(is_active);
            CREATE INDEX IF NOT EXISTS idx_media_files_created_at ON media_files(created_at);
            CREATE INDEX IF NOT EXISTS idx_validation_logs_media_file_id ON file_validation_logs(media_file_id);
            CREATE INDEX IF NOT EXISTS idx_cleanup_logs_media_file_id ON file_cleanup_logs(media_file_id);
            """
        else:  # SQLite
            initial_sql = """
            -- Initial schema for Media Management Service (SQLite)
            CREATE TABLE IF NOT EXISTS media_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                original_filename VARCHAR(255) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                file_size INTEGER NOT NULL,
                file_type VARCHAR(50) NOT NULL,
                mime_type VARCHAR(100) NOT NULL,
                file_hash VARCHAR(64) NOT NULL,
                metadata TEXT,
                is_active BOOLEAN DEFAULT 1,
                cleanup_status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS file_validation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_file_id INTEGER REFERENCES media_files(id),
                validation_type VARCHAR(50) NOT NULL,
                is_valid BOOLEAN NOT NULL,
                validation_details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS file_cleanup_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_file_id INTEGER REFERENCES media_files(id),
                cleanup_type VARCHAR(50) NOT NULL,
                success BOOLEAN NOT NULL,
                file_size_freed INTEGER DEFAULT 0,
                cleanup_details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Indexes
            CREATE INDEX IF NOT EXISTS idx_media_files_account_id ON media_files(account_id);
            CREATE INDEX IF NOT EXISTS idx_media_files_file_hash ON media_files(file_hash);
            CREATE INDEX IF NOT EXISTS idx_media_files_is_active ON media_files(is_active);
            CREATE INDEX IF NOT EXISTS idx_media_files_created_at ON media_files(created_at);
            CREATE INDEX IF NOT EXISTS idx_validation_logs_media_file_id ON file_validation_logs(media_file_id);
            CREATE INDEX IF NOT EXISTS idx_cleanup_logs_media_file_id ON file_cleanup_logs(media_file_id);
            """
        
        self.apply_migration(
            version="001",
            name="initial_schema",
            sql=initial_sql
        )
    
    def run_migrations(self, migrations_dir: str = "migrations"):
        """Run all pending migrations"""
        self.ensure_migrations_table()
        applied_migrations = self.get_applied_migrations()
        
        if not os.path.exists(migrations_dir):
            logger.info("No migrations directory found, creating initial schema")
            self.create_initial_schema()
            return
        
        # Get all migration files
        migration_files = []
        for filename in os.listdir(migrations_dir):
            if filename.endswith('.sql'):
                version = filename.split('_')[0]
                migration_files.append((version, filename))
        
        # Sort by version
        migration_files.sort(key=lambda x: x[0])
        
        # Apply pending migrations
        for version, filename in migration_files:
            if version not in applied_migrations:
                filepath = os.path.join(migrations_dir, filename)
                with open(filepath, 'r') as f:
                    sql = f.read()
                
                name = filename.replace('.sql', '').replace(f'{version}_', '')
                self.apply_migration(version, name, sql)
    
    def check_connection(self) -> bool:
        """Check database connection"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def get_schema_info(self) -> dict:
        """Get database schema information"""
        try:
            metadata = MetaData()
            metadata.reflect(bind=self.engine)
            
            tables_info = {}
            for table_name, table in metadata.tables.items():
                tables_info[table_name] = {
                    'columns': [col.name for col in table.columns],
                    'indexes': [idx.name for idx in table.indexes]
                }
            
            return {
                'connected': True,
                'tables': tables_info,
                'table_count': len(tables_info)
            }
            
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }
    
    def backup_schema(self, output_file: str):
        """Backup database schema"""
        try:
            # This is a simplified backup - in production, use pg_dump
            metadata = MetaData()
            metadata.reflect(bind=self.engine)
            
            schema_info = {
                'timestamp': datetime.utcnow().isoformat(),
                'database_url': self.database_url.split('@')[1].split('/')[0] if '@' in self.database_url else 'hidden',
                'tables': {}
            }
            
            for table_name, table in metadata.tables.items():
                schema_info['tables'][table_name] = {
                    'columns': [
                        {
                            'name': col.name,
                            'type': str(col.type),
                            'nullable': col.nullable,
                            'primary_key': col.primary_key
                        }
                        for col in table.columns
                    ]
                }
            
            with open(output_file, 'w') as f:
                json.dump(schema_info, f, indent=2)
            
            logger.info(f"Schema backup saved to {output_file}")
            
        except Exception as e:
            logger.error(f"Schema backup failed: {e}")
            raise
    
    def reset_database(self):
        """Reset database (DANGER: This will delete all data)"""
        try:
            metadata = MetaData()
            metadata.reflect(bind=self.engine)
            metadata.drop_all(bind=self.engine)
            
            # Recreate schema
            self.create_initial_schema()
            
            logger.info("Database reset completed")
            
        except Exception as e:
            logger.error(f"Database reset failed: {e}")
            raise

def main():
    """CLI interface for database management"""
    if len(sys.argv) < 2:
        print("Usage: python db_manager.py <command> [args]")
        print("Commands:")
        print("  migrate - Run pending migrations")
        print("  check - Check database connection")
        print("  info - Get schema information")
        print("  backup <file> - Backup schema to file")
        print("  reset - Reset database (DANGER)")
        sys.exit(1)
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    db_manager = DatabaseManager(database_url)
    command = sys.argv[1]
    
    if command == 'migrate':
        db_manager.run_migrations()
        print("✅ Migrations completed")
    
    elif command == 'check':
        if db_manager.check_connection():
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
            sys.exit(1)
    
    elif command == 'info':
        info = db_manager.get_schema_info()
        print(json.dumps(info, indent=2))
    
    elif command == 'backup':
        if len(sys.argv) < 3:
            print("Usage: python db_manager.py backup <output_file>")
            sys.exit(1)
        
        output_file = sys.argv[2]
        db_manager.backup_schema(output_file)
    
    elif command == 'reset':
        confirm = input("⚠️  This will DELETE ALL DATA. Type 'CONFIRM' to proceed: ")
        if confirm == 'CONFIRM':
            db_manager.reset_database()
            print("✅ Database reset completed")
        else:
            print("❌ Reset cancelled")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == '__main__':
    main()

