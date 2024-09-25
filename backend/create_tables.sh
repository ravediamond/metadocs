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
  -- Enable the pgvector extension for vector-based similarity search
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

  -- Create Concepts table
  CREATE TABLE IF NOT EXISTS concepts (
    concept_id UUID PRIMARY KEY,
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50),  -- 'definition', 'process', 'methodology', etc.
    embedding VECTOR(1536),  -- pgvector embedding for similarity
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- Create Concept Relationships table
  CREATE TABLE IF NOT EXISTS concept_relationships (
    relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    concept_id_1 UUID REFERENCES concepts(concept_id) ON DELETE CASCADE,
    concept_id_2 UUID REFERENCES concepts(concept_id) ON DELETE CASCADE,
    relationship_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

  -- Create Sources table
  CREATE TABLE IF NOT EXISTS sources (
    source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50),  -- 'table', 'database', 'api'
    location TEXT NOT NULL,  -- URI, table name, or connection string
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- Create Methodologies table
  CREATE TABLE IF NOT EXISTS methodologies (
    methodology_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    steps TEXT NOT NULL,  -- Detailed steps on how to join sources or get data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- Create User Settings table
  CREATE TABLE IF NOT EXISTS user_settings (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    setting_key VARCHAR(100) NOT NULL,
    setting_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, setting_key)
  );

  -- Create User Domain Settings table
  CREATE TABLE IF NOT EXISTS user_domain_settings (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
    setting_key VARCHAR(100) NOT NULL,
    setting_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, domain_id, setting_key)
  );

  -- Indexes
  CREATE INDEX IF NOT EXISTS email_index ON users (email);
  CREATE INDEX IF NOT EXISTS owner_user_id_index ON domains (owner_user_id);

EOSQL

echo "Tables created successfully."

echo "Inserting initial data into tables..."

# Insert initial data for users
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

  -- Insert concepts for the Sales domain
  INSERT INTO concepts (concept_id, domain_id, name, description, type, embedding, created_at, updated_at)
  VALUES
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Total Sales', 'Total sales for a specific period', 'definition', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Monthly Sales', 'Sales data for each month', 'definition', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Sales Target', 'Targeted sales figure for the month', 'definition', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Quarterly Sales', 'Sales grouped by quarter', 'definition', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Yearly Sales', 'Sales grouped by year', 'definition', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Sales Revenue', 'Total revenue generated from sales', 'definition', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Sales Forecast', 'Projected sales for the upcoming period', 'definition', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

  -- Insert relationships between concepts
  INSERT INTO concept_relationships (concept_id_1, concept_id_2, relationship_type, created_at)
  VALUES
      ((SELECT concept_id FROM concepts WHERE name = 'Monthly Sales'), (SELECT concept_id FROM concepts WHERE name = 'Quarterly Sales'), 'part_of', CURRENT_TIMESTAMP),
      ((SELECT concept_id FROM concepts WHERE name = 'Quarterly Sales'), (SELECT concept_id FROM concepts WHERE name = 'Yearly Sales'), 'part_of', CURRENT_TIMESTAMP),
      ((SELECT concept_id FROM concepts WHERE name = 'Sales Revenue'), (SELECT concept_id FROM concepts WHERE name = 'Monthly Sales'), 'related_to', CURRENT_TIMESTAMP),
      ((SELECT concept_id FROM concepts WHERE name = 'Sales Forecast'), (SELECT concept_id FROM concepts WHERE name = 'Sales Revenue'), 'depends_on', CURRENT_TIMESTAMP);

  -- Insert sources for the Sales domain
  INSERT INTO sources (source_id, domain_id, name, source_type, location, description, created_at)
  VALUES
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Sales Data Table', 'table', 'db.sales_data', 'Table containing raw sales data', CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Customer Data API', 'api', 'https://api.company.com/customers', 'API endpoint for customer information', CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Product Information Table', 'table', 'db.products', 'Table containing product information', CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Sales Targets Table', 'table', 'db.sales_targets', 'Table with monthly sales targets', CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Sales Forecast API', 'api', 'https://api.company.com/forecast', 'API endpoint providing sales forecast data', CURRENT_TIMESTAMP);

  -- Insert methodologies for the Sales domain
  INSERT INTO methodologies (methodology_id, domain_id, name, description, steps, created_at)
  VALUES
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Calculate Total Sales', 'Methodology to calculate total sales', '1. Fetch raw sales data from db.sales_data; 2. Group by product_id; 3. Sum total sales amount.', CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Monthly Sales Report', 'Methodology to generate monthly sales report', '1. Fetch sales data from db.sales_data; 2. Join with db.sales_targets for targets; 3. Calculate performance percentage by comparing sales vs target.', CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Sales Forecasting', 'Steps to generate a sales forecast', '1. Call API https://api.company.com/forecast; 2. Parse forecast data; 3. Compare with historical sales data from db.sales_data to project trends.', CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Customer Segmentation for Sales Analysis', 'Methodology for segmenting customers based on purchase behavior', '1. Fetch customer data from https://api.company.com/customers; 2. Classify customers into segments based on sales data from db.sales_data.', CURRENT_TIMESTAMP);
EOSQL

echo "Data inserted successfully."