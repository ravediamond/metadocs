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

  -- Create Domains table with version column and composite primary key
  CREATE TABLE IF NOT EXISTS domains (
    domain_id UUID NOT NULL,
    version INT NOT NULL DEFAULT 1,
    domain_name VARCHAR(255) NOT NULL,
    owner_user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (domain_id, version)
  );

  -- Create Concepts table with domain_version column and composite primary key
  CREATE TABLE IF NOT EXISTS concepts (
    concept_id UUID NOT NULL,
    domain_id UUID NOT NULL,
    domain_version INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50),
    embedding VECTOR(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (concept_id, domain_version),
    FOREIGN KEY (domain_id, domain_version) REFERENCES domains(domain_id, version) ON DELETE CASCADE
  );

  -- Create Sources table with domain_version column and composite primary key
  CREATE TABLE IF NOT EXISTS sources (
    source_id UUID NOT NULL,
    domain_id UUID NOT NULL,
    domain_version INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50),
    location TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_id, domain_version),
    FOREIGN KEY (domain_id, domain_version) REFERENCES domains(domain_id, version) ON DELETE CASCADE
  );

  -- Create Methodologies table with domain_version column and composite primary key
  CREATE TABLE IF NOT EXISTS methodologies (
    methodology_id UUID NOT NULL,
    domain_id UUID NOT NULL,
    domain_version INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    steps TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (methodology_id, domain_version),
    FOREIGN KEY (domain_id, domain_version) REFERENCES domains(domain_id, version) ON DELETE CASCADE
  );

  -- Create Relationships table with domain_version column and composite primary key
  CREATE TABLE IF NOT EXISTS relationships (
    relationship_id UUID NOT NULL,
    domain_id UUID NOT NULL,
    domain_version INT NOT NULL,
    entity_id_1 UUID NOT NULL,
    entity_type_1 VARCHAR(50) NOT NULL,
    entity_id_2 UUID NOT NULL,
    entity_type_2 VARCHAR(50) NOT NULL,
    relationship_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (relationship_id, domain_version),
    FOREIGN KEY (domain_id, domain_version) REFERENCES domains(domain_id, version) ON DELETE CASCADE
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

  -- Create Roles table
  CREATE TABLE IF NOT EXISTS roles (
    role_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
  );

  -- Create UserRoles table
  CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(role_id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, domain_id, role_id)
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
  INSERT INTO domains (domain_id, version, domain_name, owner_user_id, description, created_at)
  VALUES
    ('d11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1, 'Sales', 'b11f11d1-1c1c-41f1-bf2d-4bfbf1c1d1d1', 'This is a Sales example domain', CURRENT_TIMESTAMP),
    ('d22d22d2-2a2a-42a2-bf2a-4cfcf2b2d2d2', 1, 'IT', 'b22f22d2-2c2c-42f2-bf3d-4cfcf2c2e2e2', 'This is an IT domain', CURRENT_TIMESTAMP);

  -- Insert concepts for Sales domain
  INSERT INTO concepts (concept_id, domain_id, domain_version, name, description, type, embedding, created_at, updated_at)
  VALUES
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1, 'Total Sales', 'Total sales for a specific period', 'definition', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1, 'Monthly Sales', 'Sales data for each month', 'definition', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1, 'Quarterly Sales', 'Sales data for each quarter', 'definition', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1, 'Sales Forecast', 'Predicted future sales based on current trends', 'definition', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1, 'Customer Retention', 'The rate at which customers return to make purchases', 'definition', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

  -- Insert sources for Sales domain
  INSERT INTO sources (source_id, domain_id, domain_version, name, source_type, location, description, created_at)
  VALUES
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1, 'Sales Data Table', 'table', 'db.sales_data', 'Table containing raw sales data', CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1, 'Customer Data API', 'api', 'https://api.company.com/customers', 'API endpoint for customer information', CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1, 'Sales Forecasting API', 'api', 'https://api.company.com/forecast', 'API for sales forecasting data', CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1, 'Customer Feedback Data', 'table', 'db.customer_feedback', 'Table containing customer feedback', CURRENT_TIMESTAMP);

  -- Insert methodologies for Sales domain
  INSERT INTO methodologies (methodology_id, domain_id, domain_version, name, description, steps, created_at)
  VALUES
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1, 'Calculate Total Sales', 'Methodology to calculate total sales', '1. Fetch raw sales data from db.sales_data; 2. Group by product_id; 3. Sum total sales amount.', CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1, 'Analyze Monthly Sales', 'Methodology to analyze monthly sales trends', '1. Fetch monthly sales data; 2. Analyze by month.', CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1, 'Sales Forecasting', 'Methodology to forecast future sales', '1. Fetch current sales data; 2. Use predictive analytics models from Sales Forecasting API.', CURRENT_TIMESTAMP),
      (gen_random_uuid(), 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1, 'Customer Retention Analysis', 'Methodology to calculate and improve customer retention', '1. Fetch customer feedback and sales data; 2. Identify repeat customers.', CURRENT_TIMESTAMP);

  -- Insert relationships for the Sales domain
  INSERT INTO relationships (relationship_id, domain_id, domain_version, entity_id_1, entity_type_1, entity_id_2, entity_type_2, relationship_type, created_at)
  VALUES
    -- Relationship between concept 'Total Sales' and methodology 'Calculate Total Sales'
    (gen_random_uuid(),
      'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1,
      (SELECT concept_id FROM concepts WHERE name = 'Total Sales' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1' AND domain_version = 1), 
      'concept', 
      (SELECT methodology_id FROM methodologies WHERE name = 'Calculate Total Sales' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1' AND domain_version = 1), 
      'methodology', 
      'uses', 
      CURRENT_TIMESTAMP),

    -- Relationship between concept 'Monthly Sales' and methodology 'Analyze Monthly Sales'
    (gen_random_uuid(),
      'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1,
      (SELECT concept_id FROM concepts WHERE name = 'Monthly Sales' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1' AND domain_version = 1), 
      'concept', 
      (SELECT methodology_id FROM methodologies WHERE name = 'Analyze Monthly Sales' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1' AND domain_version = 1), 
      'methodology', 
      'uses', 
      CURRENT_TIMESTAMP),

    -- Relationship between 'Total Sales' concept and 'Sales Data Table' source
    (gen_random_uuid(),
      'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1,
      (SELECT concept_id FROM concepts WHERE name = 'Total Sales' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1' AND domain_version = 1),
      'concept',
      (SELECT source_id FROM sources WHERE name = 'Sales Data Table' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1' AND domain_version = 1),
      'source',
      'depends_on', 
      CURRENT_TIMESTAMP),

    -- Relationship between 'Monthly Sales' concept and 'Sales Data Table' source
    (gen_random_uuid(),
      'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1,
      (SELECT concept_id FROM concepts WHERE name = 'Monthly Sales' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1' AND domain_version = 1),
      'concept',
      (SELECT source_id FROM sources WHERE name = 'Sales Data Table' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1' AND domain_version = 1),
      'source',
      'depends_on', 
      CURRENT_TIMESTAMP),

    -- Relationship between 'Customer Data API' source and 'Calculate Total Sales' methodology
    (gen_random_uuid(),
      'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1,
      (SELECT source_id FROM sources WHERE name = 'Customer Data API' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1' AND domain_version = 1),
      'source',
      (SELECT methodology_id FROM methodologies WHERE name = 'Calculate Total Sales' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1' AND domain_version = 1),
      'methodology',
      'provides', 
      CURRENT_TIMESTAMP),

    -- Relationship between 'Customer Retention' concept and 'Customer Feedback Data' source
    (gen_random_uuid(),
      'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1,
      (SELECT concept_id FROM concepts WHERE name = 'Customer Retention' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1' AND domain_version = 1),
      'concept',
      (SELECT source_id FROM sources WHERE name = 'Customer Feedback Data' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1' AND domain_version = 1),
      'source',
      'depends_on', 
      CURRENT_TIMESTAMP),

    -- Relationship between 'Sales Forecast' concept and 'Sales Forecasting API' source
    (gen_random_uuid(),
      'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1', 1,
      (SELECT concept_id FROM concepts WHERE name = 'Sales Forecast' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1' AND domain_version = 1),
      'concept',
      (SELECT source_id FROM sources WHERE name = 'Sales Forecasting API' AND domain_id = 'd11d11d1-1a1a-41a1-bf1a-4bfbf1b1d1d1' AND domain_version = 1),
      'source',
      'depends_on', 
      CURRENT_TIMESTAMP);

  INSERT INTO roles (role_name, description)
  VALUES
    ('owner', 'Full access to the domain, including managing roles'),
    ('admin', 'Administrative access to the domain'),
    ('member', 'Can contribute to the domain'),
    ('viewer', 'Can view domain content')
  ON CONFLICT (role_name) DO NOTHING;


EOSQL

echo "Data inserted successfully."