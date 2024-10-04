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
  -- Enable error stopping
  \set ON_ERROR_STOP on

  -- Enable the pgcrypto extension for gen_random_uuid()
  CREATE EXTENSION IF NOT EXISTS pgcrypto;

  -- Enable the pgvector extension for vector-based similarity search
  CREATE EXTENSION IF NOT EXISTS vector;

  -- Create Tenants table
  CREATE TABLE IF NOT EXISTS tenants (
    tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- Create Users table
  CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- Create Domains table with tenant_id
  CREATE TABLE IF NOT EXISTS domains (
    domain_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    domain_name VARCHAR(255) NOT NULL,
    owner_user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- Create DomainVersions table with tenant_id
  CREATE TABLE IF NOT EXISTS domain_versions (
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    version INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (domain_id, version)
  );

  -- Create Concepts table with tenant_id
  CREATE TABLE IF NOT EXISTS concepts (
    concept_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID NOT NULL REFERENCES domains(domain_id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    domain_version INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50),
    embedding VECTOR(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (domain_id, domain_version) REFERENCES domain_versions(domain_id, version) ON DELETE CASCADE
  );

  -- Create Sources table with tenant_id
  CREATE TABLE IF NOT EXISTS sources (
    source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID NOT NULL REFERENCES domains(domain_id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    domain_version INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50),
    location TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (domain_id, domain_version) REFERENCES domain_versions(domain_id, version) ON DELETE CASCADE
  );

  -- Create Methodologies table with tenant_id
  CREATE TABLE IF NOT EXISTS methodologies (
    methodology_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID NOT NULL REFERENCES domains(domain_id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    domain_version INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    steps TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (domain_id, domain_version) REFERENCES domain_versions(domain_id, version) ON DELETE CASCADE
  );

  -- Create Relationships table with tenant_id
  CREATE TABLE IF NOT EXISTS relationships (
    relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID NOT NULL REFERENCES domains(domain_id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    domain_version INT NOT NULL,
    entity_id_1 UUID NOT NULL,
    entity_type_1 VARCHAR(50) NOT NULL,
    entity_id_2 UUID NOT NULL,
    entity_type_2 VARCHAR(50) NOT NULL,
    relationship_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (domain_id, domain_version) REFERENCES domain_versions(domain_id, version) ON DELETE CASCADE
  );

  -- Create User Config table
  CREATE TABLE IF NOT EXISTS user_config (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    config_key VARCHAR(255) NOT NULL,
    config_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- Create Domain Config table
  CREATE TABLE IF NOT EXISTS domain_config (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
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
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked TIMESTAMP
  );

  -- Create Roles table with tenant_id
  CREATE TABLE IF NOT EXISTS roles (
    role_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    role_name VARCHAR(50) NOT NULL,
    description TEXT,
    UNIQUE (tenant_id, role_name)
  );

  -- Create UserRoles table
  CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(role_id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, domain_id)
  );

  -- Create UserTenants association table
  CREATE TABLE IF NOT EXISTS user_tenants (
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(role_id) ON DELETE CASCADE,  -- Add this line for role_id
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Optionally add this for consistency with other tables
    PRIMARY KEY (user_id, tenant_id)
  );
EOSQL

echo "Tables created successfully."

echo "Inserting initial data into tables..."

# Insert initial data for tenants, users, domains, etc.
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-'EOSQL'
  -- Enable error stopping
  \set ON_ERROR_STOP on

  BEGIN;

  -- Insert data into Tenants table
  INSERT INTO tenants (tenant_id, tenant_name)
  VALUES
    (gen_random_uuid(), 'Tenant One')
  ON CONFLICT (tenant_id) DO NOTHING;

  -- Insert data into Users table
  INSERT INTO users (user_id, email, hashed_password, name)
  VALUES
    (gen_random_uuid(), 'user1@example.com', '$2b$12$ctUeogp4nb3cbMERRe1qVeRfgh3aIxP7clgEPgu1A.JrUOv6apnT2', 'User One'),
    (gen_random_uuid(), 'user2@example.com', '$2b$12$RaerUrFIbqkUomI.4YWnROJ419pK2h8Fbs/4bIBlaviSzKoXwutJK', 'User Two')
  ON CONFLICT (user_id) DO NOTHING;

-- Associate users with the tenant and assign roles
  INSERT INTO user_tenants (user_id, tenant_id, role_id)
  VALUES
    ((SELECT user_id FROM users WHERE email = 'user1@example.com'), 
    (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 
    (SELECT role_id FROM roles WHERE role_name = 'Owner' AND tenant_id = (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'))),

    ((SELECT user_id FROM users WHERE email = 'user2@example.com'), 
    (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'),
    (SELECT role_id FROM roles WHERE role_name = 'Member' AND tenant_id = (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One')))
  ON CONFLICT (user_id, tenant_id) DO NOTHING;

  -- Insert data into Domains table
  INSERT INTO domains (domain_id, tenant_id, domain_name, owner_user_id, description, created_at)
  VALUES
    (gen_random_uuid(), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'Sales', (SELECT user_id FROM users WHERE email = 'user1@example.com'), 'This is a Sales example domain', CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'IT', (SELECT user_id FROM users WHERE email = 'user2@example.com'), 'This is an IT domain', CURRENT_TIMESTAMP)
  ON CONFLICT (domain_id) DO NOTHING;

  -- Insert data into DomainVersions table
  INSERT INTO domain_versions (domain_id, tenant_id, version, created_at)
  VALUES
    ((SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 1, CURRENT_TIMESTAMP),
    ((SELECT domain_id FROM domains WHERE domain_name = 'IT'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 1, CURRENT_TIMESTAMP)
  ON CONFLICT (domain_id, version) DO NOTHING;

  -- Insert default roles into the Roles table
  INSERT INTO roles (role_id, tenant_id, role_name, description)
  VALUES
    (gen_random_uuid(), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'Owner', 'Full access to the domain, including managing roles'),
    (gen_random_uuid(), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'Admin', 'Administrative access to the domain'),
    (gen_random_uuid(), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'Member', 'Can contribute to the domain'),
    (gen_random_uuid(), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'Viewer', 'Can view domain content')
  ON CONFLICT (tenant_id, role_name) DO NOTHING;

  -- Assign 'Owner' role to each domain owner for their own domain
  INSERT INTO user_roles (user_id, domain_id, role_id)
  SELECT owner_user_id, domain_id, (SELECT role_id FROM roles WHERE role_name = 'Owner' AND tenant_id = domains.tenant_id LIMIT 1)
  FROM domains
  ON CONFLICT (user_id, domain_id) DO NOTHING;

  -- Assign 'Member' role to user1 for the IT domain
  INSERT INTO user_roles (user_id, domain_id, role_id)
  VALUES
    ((SELECT user_id FROM users WHERE email = 'user1@example.com'), (SELECT domain_id FROM domains WHERE domain_name = 'IT'), (SELECT role_id FROM roles WHERE role_name = 'Member' AND tenant_id = (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One') LIMIT 1))
  ON CONFLICT (user_id, domain_id) DO NOTHING;

  -- Assign 'Viewer' role to user2 for the Sales domain
  INSERT INTO user_roles (user_id, domain_id, role_id)
  VALUES
    ((SELECT user_id FROM users WHERE email = 'user2@example.com'), (SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT role_id FROM roles WHERE role_name = 'Viewer' AND tenant_id = (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One') LIMIT 1))
  ON CONFLICT (user_id, domain_id) DO NOTHING;

  -- Insert concepts for Sales domain
  INSERT INTO concepts (concept_id, domain_id, tenant_id, domain_version, name, description, type, embedding, created_at, updated_at)
  VALUES
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 1, 'Total Sales', 'Total sales for a specific period', 'definition', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 1, 'Monthly Sales', 'Sales data for each month', 'definition', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 1, 'Quarterly Sales', 'Sales data for each quarter', 'definition', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 1, 'Sales Forecast', 'Predicted future sales based on current trends', 'definition', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 1, 'Customer Retention', 'The rate at which customers return to make purchases', 'definition', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
  ON CONFLICT (concept_id) DO NOTHING;

  -- Insert sources for Sales domain
  INSERT INTO sources (source_id, domain_id, tenant_id, domain_version, name, source_type, location, description, created_at)
  VALUES
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 1, 'Sales Data Table', 'table', 'db.sales_data', 'Table containing raw sales data', CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 1, 'Customer Data API', 'api', 'https://api.company.com/customers', 'API endpoint for customer information', CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 1, 'Sales Forecasting API', 'api', 'https://api.company.com/forecast', 'API for sales forecasting data', CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 1, 'Customer Feedback Data', 'table', 'db.customer_feedback', 'Table containing customer feedback', CURRENT_TIMESTAMP)
  ON CONFLICT (source_id) DO NOTHING;

  -- Insert methodologies for Sales domain
  INSERT INTO methodologies (methodology_id, domain_id, tenant_id, domain_version, name, description, steps, created_at)
  VALUES
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 1, 'Calculate Total Sales', 'Methodology to calculate total sales', '1. Fetch raw sales data from db.sales_data; 2. Group by product_id; 3. Sum total sales amount.', CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 1, 'Analyze Monthly Sales', 'Methodology to analyze monthly sales trends', '1. Fetch monthly sales data; 2. Analyze by month.', CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 1, 'Sales Forecasting', 'Methodology to forecast future sales', '1. Fetch current sales data; 2. Use predictive analytics models from Sales Forecasting API.', CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 1, 'Customer Retention Analysis', 'Methodology to calculate and improve customer retention', '1. Fetch customer feedback and sales data; 2. Identify repeat customers.', CURRENT_TIMESTAMP)
  ON CONFLICT (methodology_id) DO NOTHING;

  -- Insert relationships for the Sales domain
  INSERT INTO relationships (relationship_id, domain_id, tenant_id, domain_version, entity_id_1, entity_type_1, entity_id_2, entity_type_2, relationship_type, created_at)
  VALUES
    (gen_random_uuid(),
      (SELECT domain_id FROM domains WHERE domain_name = 'Sales'),
      (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'),
      1,
      (SELECT concept_id FROM concepts WHERE name = 'Total Sales' AND domain_id = (SELECT domain_id FROM domains WHERE domain_name = 'Sales') LIMIT 1),
      'concept',
      (SELECT methodology_id FROM methodologies WHERE name = 'Calculate Total Sales' AND domain_id = (SELECT domain_id FROM domains WHERE domain_name = 'Sales') LIMIT 1),
      'methodology',
      'uses',
      CURRENT_TIMESTAMP),
    (gen_random_uuid(),
      (SELECT domain_id FROM domains WHERE domain_name = 'Sales'),
      (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'),
      1,
      (SELECT concept_id FROM concepts WHERE name = 'Monthly Sales' AND domain_id = (SELECT domain_id FROM domains WHERE domain_name = 'Sales') LIMIT 1),
      'concept',
      (SELECT methodology_id FROM methodologies WHERE name = 'Analyze Monthly Sales' AND domain_id = (SELECT domain_id FROM domains WHERE domain_name = 'Sales') LIMIT 1),
      'methodology',
      'uses',
      CURRENT_TIMESTAMP),
    (gen_random_uuid(),
      (SELECT domain_id FROM domains WHERE domain_name = 'Sales'),
      (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'),
      1,
      (SELECT concept_id FROM concepts WHERE name = 'Total Sales' AND domain_id = (SELECT domain_id FROM domains WHERE domain_name = 'Sales') LIMIT 1),
      'concept',
      (SELECT source_id FROM sources WHERE name = 'Sales Data Table' AND domain_id = (SELECT domain_id FROM domains WHERE domain_name = 'Sales') LIMIT 1),
      'source',
      'depends_on',
      CURRENT_TIMESTAMP)
  ON CONFLICT (relationship_id) DO NOTHING;

  -- Insert data into User Config table
  INSERT INTO user_config (config_id, user_id, tenant_id, config_key, config_value, created_at)
  VALUES
    (gen_random_uuid(), (SELECT user_id FROM users WHERE email = 'user1@example.com'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'theme', 'dark', CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT user_id FROM users WHERE email = 'user1@example.com'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'notifications', 'enabled', CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT user_id FROM users WHERE email = 'user2@example.com'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'theme', 'light', CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT user_id FROM users WHERE email = 'user2@example.com'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'notifications', 'disabled', CURRENT_TIMESTAMP)
  ON CONFLICT (config_id) DO NOTHING;

  -- Insert data into Domain Config table
  INSERT INTO domain_config (config_id, domain_id, tenant_id, config_key, config_value, created_at)
  VALUES
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'default_language', 'en', CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'time_zone', 'UTC', CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'IT'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'default_language', 'es', CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'IT'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'time_zone', 'CET', CURRENT_TIMESTAMP)
  ON CONFLICT (config_id) DO NOTHING;

  COMMIT;
EOSQL

echo "Data inserted successfully."