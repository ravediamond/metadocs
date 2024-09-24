#!/bin/sh

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
    user_id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- Create Domains table
  CREATE TABLE IF NOT EXISTS domains (
    domain_id UUID PRIMARY KEY,
    domain_name VARCHAR(255) NOT NULL,
    owner_user_id UUID REFERENCES users(user_id),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- Indexes
  CREATE INDEX IF NOT EXISTS email_index ON users (email);
  CREATE INDEX IF NOT EXISTS owner_user_id_index ON domains (owner_user_id);
EOSQL

echo "Tables created successfully."

echo "Inserting initial data into tables..."

# Insert initial data for users
# user1@example.com password1
# user2@example.com password2
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-'EOSQL'
  -- Insert data into Users table
  INSERT INTO users (user_id, email, hashed_password, name)
  VALUES
    ('b11f11d1-1c1c-41f1-bf2d-4bfbf1c1d1d1', 'user1@example.com', '$2b$12$ctUeogp4nb3cbMERRe1qVeRfgh3aIxP7clgEPgu1A.JrUOv6apnT2', 'User One'),
    ('b22f22d2-2c2c-42f2-bf3d-4cfcf2c2e2e2', 'user2@example.com', '$2b$12$RaerUrFIbqkUomI.4YWnROJ419pK2h8Fbs/4bIBlaviSzKoXwutJK', 'User Two');
EOSQL

# Insert initial data for domains
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-EOSQL
  -- Insert data into Domains table
  INSERT INTO domains (domain_id, domain_name, owner_user_id, description, created_at)
  VALUES
    ('d11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Sales', 'b11f11d1-1c1c-41f1-bf2d-4bfbf1c1d1d1', 'This is a Sales example domain', CURRENT_TIMESTAMP),
    ('d22d22d2-2a2a-42a2-bf2a-4cfcf2b2d2d2', 'IT', 'b22f22d2-2c2c-42f2-bf3d-4cfcf2c2e2e2', 'This is an IT domain', CURRENT_TIMESTAMP);
EOSQL

echo "Data inserted successfully."