#!/bin/bash
# Database restore script for Zion Market Analysis Platform
# This script restores the PostgreSQL database from a backup file

# Exit on error
set -e

# Load environment variables
if [ -f "../.env" ]; then
  source ../.env
fi

# Configuration
BACKUP_DIR="/app/backups"
DB_USER=${POSTGRES_USER:-postgres}
DB_NAME=${POSTGRES_DB:-ziondb}
DB_HOST=${POSTGRES_HOST:-db}
DB_PASSWORD=${POSTGRES_PASSWORD}

# Check if a specific backup file was provided
if [ -z "$1" ]; then
  # If no backup file specified, use the latest one
  BACKUP_FILE="$BACKUP_DIR/latest_backup.sql.gz"
  if [ ! -L "$BACKUP_FILE" ]; then
    echo "Error: No latest backup found at $BACKUP_FILE"
    echo "Available backups:"
    ls -la $BACKUP_DIR/*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
  fi
else
  # Use the specified backup file
  BACKUP_FILE="$1"
  if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
  fi
fi

echo "Starting database restore from $BACKUP_FILE at $(date)"
echo "Warning: This will overwrite the current database!"
echo "Press Ctrl+C within 10 seconds to cancel..."
sleep 10

# Create a temporary directory for the uncompressed backup
TEMP_DIR=$(mktemp -d)
UNCOMPRESSED_BACKUP="$TEMP_DIR/backup.sql"

echo "Uncompressing backup file..."
gunzip -c "$BACKUP_FILE" > "$UNCOMPRESSED_BACKUP"

echo "Dropping existing database..."
PGPASSWORD="$DB_PASSWORD" psql -h $DB_HOST -U $DB_USER -c "DROP DATABASE IF EXISTS $DB_NAME;"
echo "Creating fresh database..."
PGPASSWORD="$DB_PASSWORD" psql -h $DB_HOST -U $DB_USER -c "CREATE DATABASE $DB_NAME;"

echo "Restoring from backup..."
PGPASSWORD="$DB_PASSWORD" pg_restore \
  -h $DB_HOST \
  -U $DB_USER \
  -d $DB_NAME \
  --no-owner \
  --role=$DB_USER \
  "$UNCOMPRESSED_BACKUP"

# Check if restore was successful
if [ $? -eq 0 ]; then
  echo "Database restore completed successfully at $(date)"
else
  echo "Warning: Restore completed with some errors. Please check the database."
fi

# Clean up
rm -rf $TEMP_DIR
echo "Cleanup completed"

# Optionally run migrations to ensure schema is up to date
read -p "Run migrations to ensure schema is up to date? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "Running migrations..."
  cd ../../
  alembic upgrade head
  echo "Migrations completed"
fi