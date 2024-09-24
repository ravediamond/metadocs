#!/bin/sh

# Log the environment variables to ensure they are set
echo "POSTGRES_HOST: $POSTGRES_HOST"
echo "POSTGRES_USER: $POSTGRES_USER"
echo "POSTGRES_DB: $POSTGRES_DB"

# Export the PostgreSQL password for psql to use
export PGPASSWORD=$POSTGRES_PASSWORD

# Wait for PostgreSQL to be ready with a timeout of 60 seconds
MAX_RETRIES=30
RETRY_COUNT=0

echo "Waiting for PostgreSQL to be ready..."
until psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q'; do
  RETRY_COUNT=$((RETRY_COUNT+1))

  if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
    echo "PostgreSQL is still not ready after $MAX_RETRIES retries. Exiting..."
    exit 1
  fi

  echo "PostgreSQL is not ready yet. Retrying in 2 seconds... ($RETRY_COUNT/$MAX_RETRIES)"
  sleep 2
done

echo "PostgreSQL is ready. Creating tables..."

# Create tables
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-EOSQL
  -- Enable the pgvector extension
  CREATE EXTENSION IF NOT EXISTS vector;

  -- Create Users table
  CREATE TABLE IF NOT EXISTS users (
    UserId UUID PRIMARY KEY,
    Email VARCHAR(255) UNIQUE NOT NULL,
    HashedPassword TEXT NOT NULL,
    Name VARCHAR(255) NOT NULL,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- Create Domains table
  CREATE TABLE IF NOT EXISTS domains (
    DomainId UUID PRIMARY KEY,
    DomainName VARCHAR(255) NOT NULL,
    OwnerUserId UUID REFERENCES users(UserId),
    Description TEXT,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- Indexes
  CREATE INDEX IF NOT EXISTS EmailIndex ON users (Email);
  CREATE INDEX IF NOT EXISTS OwnerUserIdIndex ON domains (OwnerUserId);
EOSQL

echo "Tables created successfully."