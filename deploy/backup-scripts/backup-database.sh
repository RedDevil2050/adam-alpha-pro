#!/bin/bash
# Database backup script for Zion Market Analysis Platform
# This script creates a daily backup of the PostgreSQL database
# and manages backup retention

# Exit on error
set -e

# Load environment variables
if [ -f "../.env" ]; then
  source ../.env
fi

# Configuration
BACKUP_DIR="/app/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/ziondb_backup_$DATE.sql.gz"
RETENTION_DAYS=14
DB_USER=${POSTGRES_USER:-postgres}
DB_NAME=${POSTGRES_DB:-ziondb}
DB_HOST=${POSTGRES_HOST:-db}
DB_PASSWORD=${POSTGRES_PASSWORD}

# Ensure backup directory exists
mkdir -p $BACKUP_DIR

echo "Starting database backup at $(date)"

# Create backup
PGPASSWORD="$DB_PASSWORD" pg_dump \
  -h $DB_HOST \
  -U $DB_USER \
  -d $DB_NAME \
  -F c \
  | gzip > $BACKUP_FILE

# Check if backup was successful
if [ $? -eq 0 ]; then
  echo "Backup completed successfully: $BACKUP_FILE"
  echo "Backup size: $(du -h $BACKUP_FILE | cut -f1)"
else
  echo "Backup failed!"
  exit 1
fi

# Remove backups older than retention period
echo "Cleaning up old backups (older than $RETENTION_DAYS days)..."
find $BACKUP_DIR -name "ziondb_backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete

# Create symlink to latest backup
ln -sf $BACKUP_FILE $BACKUP_DIR/latest_backup.sql.gz

echo "Backup process completed at $(date)"

# Optional: Upload to cloud storage
if [ ! -z "$AWS_ACCESS_KEY_ID" ] && [ ! -z "$AWS_SECRET_ACCESS_KEY" ] && [ ! -z "$AWS_BACKUP_BUCKET" ]; then
  echo "Uploading backup to S3..."
  aws s3 cp $BACKUP_FILE s3://$AWS_BACKUP_BUCKET/database_backups/
  echo "Upload completed"
fi