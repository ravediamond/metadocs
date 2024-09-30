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

# Create tables and enable extensions
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-EOSQL
  -- Enable the pgvector extension for vector-based similarity search
  CREATE EXTENSION IF NOT EXISTS vector;

  -- Create Users table
  CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- Create Domains table with version column
  CREATE TABLE IF NOT EXISTS domains (
    domain_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_name VARCHAR(255) NOT NULL,
    owner_user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    description TEXT,
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- Create Concepts table with version column
  CREATE TABLE IF NOT EXISTS concepts (
    concept_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50),
    embedding VECTOR(1536),
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- Create Sources table with version column
  CREATE TABLE IF NOT EXISTS sources (
    source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50),
    location TEXT NOT NULL,
    description TEXT,
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- Create Methodologies table with version column
  CREATE TABLE IF NOT EXISTS methodologies (
    methodology_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    steps TEXT NOT NULL,
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- Create Relationships table with version column
  CREATE TABLE IF NOT EXISTS relationships (
    relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
    entity_id_1 UUID NOT NULL,
    entity_type_1 VARCHAR(50) NOT NULL,
    entity_id_2 UUID NOT NULL,
    entity_type_2 VARCHAR(50) NOT NULL,
    relationship_type VARCHAR(50),
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- Create User Config table
  CREATE TABLE IF NOT EXISTS user_config (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    config_key VARCHAR(255) NOT NULL,
    config_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- Create Domain Config table
  CREATE TABLE IF NOT EXISTS domain_config (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
    config_key VARCHAR(255) NOT NULL,
    config_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- Indexes
  CREATE INDEX IF NOT EXISTS email_index ON users (email);
  CREATE INDEX IF NOT EXISTS owner_user_id_index ON domains (owner_user_id);

  -- Create API Keys table
  CREATE TABLE IF NOT EXISTS api_keys (
      api_key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      api_key VARCHAR(64) UNIQUE NOT NULL,
      user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      revoked TIMESTAMP
  );
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

# Insert initial data for domains, concepts, sources, methodologies, and relationships
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-EOSQL
  -- Insert data into Domains table
  INSERT INTO domains (domain_id, domain_name, owner_user_id, description, version, created_at)
  VALUES
    ('d11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Sales', 'b11f11d1-1c1c-41f1-bf2d-4bfbf1c1d1d1', 'This is a Sales example domain', 1, CURRENT_TIMESTAMP),
    ('d22d22d2-2a2a-42a2-bf2a-4cfcf2b2d2d2', 'IT', 'b22f22d2-2c2c-42f2-bf3d-4cfcf2c2e2e2', 'This is an IT domain', 1, CURRENT_TIMESTAMP);

  -- Insert concepts for Sales domain
  INSERT INTO concepts (concept_id, domain_id, name, description, type, embedding, version, created_at, updated_at)
  VALUES
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Total Sales', 'Total sales for a specific period', 'definition', NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Monthly Sales', 'Sales data for each month', 'definition', NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Quarterly Sales', 'Sales data for each quarter', 'definition', NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Sales Forecast', 'Predicted future sales based on current trends', 'definition', NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Customer Retention', 'The rate at which customers return to make purchases', 'definition', NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

  -- Insert sources for Sales domain
  INSERT INTO sources (source_id, domain_id, name, source_type, location, description, version, created_at)
  VALUES
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Sales Data Table', 'table', 'db.sales_data', 'Table containing raw sales data', 1, CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Customer Data API', 'api', 'https://api.company.com/customers', 'API endpoint for customer information', 1, CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Sales Forecasting API', 'api', 'https://api.company.com/forecast', 'API for sales forecasting data', 1, CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Customer Feedback Data', 'table', 'db.customer_feedback', 'Table containing customer feedback', 1, CURRENT_TIMESTAMP);

  -- Insert methodologies for Sales domain
  INSERT INTO methodologies (methodology_id, domain_id, name, description, steps, version, created_at)
  VALUES
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Calculate Total Sales', 'Methodology to calculate total sales', '1. Fetch raw sales data from db.sales_data; 2. Group by product_id; 3. Sum total sales amount.', 1, CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Analyze Monthly Sales', 'Methodology to analyze monthly sales trends', '1. Fetch monthly sales data; 2. Analyze by month.', 1, CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Sales Forecasting', 'Methodology to forecast future sales', '1. Fetch current sales data; 2. Use predictive analytics models from Sales Forecasting API.', 1, CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 'Customer Retention Analysis', 'Methodology to calculate and improve customer retention', '1. Fetch customer feedback and sales data; 2. Identify repeat customers.', 1, CURRENT_TIMESTAMP);

  -- Insert relationships for the Sales domain
  INSERT INTO relationships (entity_id_1, entity_type_1, entity_id_2, entity_type_2, relationship_type, version, created_at, domain_id)
  VALUES
    -- Relationship between concept 'Total Sales' and methodology 'Calculate Total Sales'
    ((SELECT concept_id FROM concepts WHERE name = 'Total Sales' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1'), 
      'concept', 
      (SELECT methodology_id FROM methodologies WHERE name = 'Calculate Total Sales' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1'), 
      'methodology', 
      'uses', 1, CURRENT_TIMESTAMP, 
      'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1'),

    -- Relationship between concept 'Monthly Sales' and methodology 'Analyze Monthly Sales'
    ((SELECT concept_id FROM concepts WHERE name = 'Monthly Sales' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1'), 
      'concept', 
      (SELECT methodology_id FROM methodologies WHERE name = 'Analyze Monthly Sales' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1'), 
      'methodology', 
      'uses', 1, CURRENT_TIMESTAMP, 
      'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1'),

    -- Relationship between 'Total Sales' concept and 'Sales Data Table' source
    ((SELECT concept_id FROM concepts WHERE name = 'Total Sales' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1'),
      'concept',
      (SELECT source_id FROM sources WHERE name = 'Sales Data Table' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1'),
      'source',
      'depends_on', 1, CURRENT_TIMESTAMP,
      'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1'),

    -- Relationship between 'Monthly Sales' concept and 'Sales Data Table' source
    ((SELECT concept_id FROM concepts WHERE name = 'Monthly Sales' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1'),
      'concept',
      (SELECT source_id FROM sources WHERE name = 'Sales Data Table' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1'),
      'source',
      'depends_on', 1, CURRENT_TIMESTAMP,
      'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1'),

    -- Relationship between 'Customer Data API' source and 'Calculate Total Sales' methodology
    ((SELECT source_id FROM sources WHERE name = 'Customer Data API' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1'),
      'source',
      (SELECT methodology_id FROM methodologies WHERE name = 'Calculate Total Sales' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1'),
      'methodology',
      'provides', 1, CURRENT_TIMESTAMP,
      'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1'),

    -- Relationship between 'Customer Retention' concept and 'Customer Feedback Data' source
    ((SELECT concept_id FROM concepts WHERE name = 'Customer Retention' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1'),
      'concept',
      (SELECT source_id FROM sources WHERE name = 'Customer Feedback Data' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1'),
      'source',
      'depends_on', 1, CURRENT_TIMESTAMP,
      'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1'),

    -- Relationship between 'Sales Forecast' concept and 'Sales Forecasting API' source
    ((SELECT concept_id FROM concepts WHERE name = 'Sales Forecast' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1'),
      'concept',
      (SELECT source_id FROM sources WHERE name = 'Sales Forecasting API' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1'),
      'source',
      'depends_on', 1, CURRENT_TIMESTAMP,
      'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1');

  -- Insert more relationships for the IT domain
  INSERT INTO relationships (entity_id_1, entity_type_1, entity_id_2, entity_type_2, relationship_type, version, created_at, domain_id)
  VALUES
    -- Relationship between 'Incident Management' concept and 'Incident Response Procedure' methodology
    ((SELECT concept_id FROM concepts WHERE name = 'Incident Management' AND domain_id = 'd22d22d2-2a2a-42a2-bf2a-4cfcf2b2d2d2'),
      'concept',
      (SELECT methodology_id FROM methodologies WHERE name = 'Incident Response Procedure' AND domain_id = 'd22d22d2-2a2a-42a2-bf2a-4cfcf2b2d2d2'),
      'methodology',
      'defines', 1, CURRENT_TIMESTAMP,
      'd22d22d2-2a2a-42a2-bf2a-4cfcf2b2d2d2'),

    -- Relationship between 'Incident Reports API' source and 'Incident Response Procedure' methodology
    ((SELECT source_id FROM sources WHERE name = 'Incident Reports API' AND domain_id = 'd22d22d2-2a2a-42a2-bf2a-4cfcf2b2d2d2'),
      'source',
      (SELECT methodology_id FROM methodologies WHERE name = 'Incident Response Procedure' AND domain_id = 'd22d22d2-2a2a-42a2-bf2a-4cfcf2b2d2d2'),
      'methodology',
      'feeds', 1, CURRENT_TIMESTAMP,
      'd22d22d2-2a2a-42a2-bf2a-4cfcf2b2d2d2'),

    -- Relationship between 'Change Management' concept and 'Change Deployment Process' methodology
    ((SELECT concept_id FROM concepts WHERE name = 'Change Management' AND domain_id = 'd22d22d2-2a2a-42a2-bf2a-4cfcf2b2d2d2'),
      'concept',
      (SELECT methodology_id FROM methodologies WHERE name = 'Change Deployment Process' AND domain_id = 'd22d22d2-2a2a-42a2-bf2a-4cfcf2b2d2d2'),
      'methodology',
      'defines', 1, CURRENT_TIMESTAMP,
      'd22d22d2-2a2a-42a2-bf2a-4cfcf2b2d2d2'),

    -- Relationship between 'Network Monitoring' concept and 'Network Logs Table' source
    ((SELECT concept_id FROM concepts WHERE name = 'Network Monitoring' AND domain_id = 'd22d22d2-2a2a-42a2-bf2a-4cfcf2b2d2d2'),
      'concept',
      (SELECT source_id FROM sources WHERE name = 'Network Logs Table' AND domain_id = 'd22d22d2-2a2a-42a2-bf2a-4cfcf2b2d2d2'),
      'source',
      'depends_on', 1, CURRENT_TIMESTAMP,
      'd22d22d2-2a2a-42a2-bf2a-4cfcf2b2d2d2'),

    -- Relationship between 'Data Backup' concept and 'Backup Servers Table' source
    ((SELECT concept_id FROM concepts WHERE name = 'Data Backup' AND domain_id = 'd22d22d2-2a2a-42a2-bf2a-4cfcf2b2d2d2'),
      'concept',
      (SELECT source_id FROM sources WHERE name = 'Backup Servers Table' AND domain_id = 'd22d22d2-2a2a-42a2-bf2a-4cfcf2b2d2d2'),
      'source',
      'depends_on', 1, CURRENT_TIMESTAMP,
      'd22d22d2-2a2a-42a2-bf2a-4cfcf2b2d2d2');
EOSQL

echo "Data inserted successfully."