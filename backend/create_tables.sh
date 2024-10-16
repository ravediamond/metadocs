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

sleep 5  # Sleep for 5 seconds to ensure PostgreSQL has completed all tasks

echo "PostgreSQL is ready. Creating tables..."

# Create tables and enable extensions
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-EOSQL
  -- Enable error stopping
  \set ON_ERROR_STOP on

  -- Enable the pgcrypto extension for gen_random_uuid()
  CREATE EXTENSION IF NOT EXISTS pgcrypto;

  -- Enable Apache AGE extension for graph database functionality
  CREATE EXTENSION IF NOT EXISTS age;

  -- Enable the pgvector extension for vector similarity search
  CREATE EXTENSION IF NOT EXISTS vector;

  -- Load the AGE library
  LOAD 'age';

  -- SET search_path = ag_catalog, public;

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
    graph_name VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (domain_id, version)
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
    role_id UUID REFERENCES roles(role_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, tenant_id)
  );

  -- Create Invitations table
  CREATE TABLE IF NOT EXISTS invitations (
    invitation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inviter_user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    invitee_email VARCHAR(255) NOT NULL,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    accepted_at TIMESTAMP
  );

  -- Create Entities table
  CREATE TABLE IF NOT EXISTS entities (
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    entity_type VARCHAR(50) NOT NULL,  -- e.g., 'concept', 'source', 'methodology'
    vector VECTOR(1536),  -- Ensure pgvector extension is enabled
    meta_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE
  );

  -- Create Relationships table
  CREATE TABLE IF NOT EXISTS relationships (
    edge_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    relationship_type VARCHAR(50) NOT NULL,
    description TEXT,
    vector VECTOR(1536),
    meta_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
    source_entity_id UUID NOT NULL,  -- Removed foreign key constraint
    target_entity_id UUID NOT NULL   -- Removed foreign key constraint
  );

  -- Indexes
  CREATE INDEX IF NOT EXISTS email_index ON users (email);
  CREATE INDEX IF NOT EXISTS owner_user_id_index ON domains (owner_user_id);

  -- Index on invitee_email for faster lookups by email
  CREATE INDEX IF NOT EXISTS invitee_email_index ON invitations (invitee_email);

  -- Index on tenant_id for faster tenant-specific queries
  CREATE INDEX IF NOT EXISTS tenant_id_index ON invitations (tenant_id);

  -- Optional: Index on domain_id if domain-specific invitations are frequent
  CREATE INDEX IF NOT EXISTS domain_id_index ON invitations (domain_id);
EOSQL

if [ $? -eq 0 ]; then
  echo "Tables created successfully."
else
  echo "Failed to create tables. Exiting..."
  exit 1
fi

echo "Inserting initial data into tables and creating graphs for domains..."

# Insert initial data for tenants, users, domains, and create graphs for domains
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-'EOSQL'
  -- Enable error stopping
  \set ON_ERROR_STOP on

  -- SET search_path = ag_catalog, public;

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

  -- Insert default roles into the Roles table
  INSERT INTO roles (role_id, tenant_id, role_name, description)
  VALUES
    (gen_random_uuid(), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'owner', 'Full access to the domain, including managing roles'),
    (gen_random_uuid(), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'admin', 'Administrative access to the domain'),
    (gen_random_uuid(), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'member', 'Can contribute to the domain'),
    (gen_random_uuid(), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'viewer', 'Can view domain content')
  ON CONFLICT (tenant_id, role_name) DO NOTHING;

  -- Associate users with the tenant and assign roles
  INSERT INTO user_tenants (user_id, tenant_id, role_id)
  VALUES
    ((SELECT user_id FROM users WHERE email = 'user1@example.com'), 
    (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 
    (SELECT role_id FROM roles WHERE role_name = 'owner' AND tenant_id = (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'))),

    ((SELECT user_id FROM users WHERE email = 'user2@example.com'), 
    (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'),
    (SELECT role_id FROM roles WHERE role_name = 'member' AND tenant_id = (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One')))
  ON CONFLICT (user_id, tenant_id) DO NOTHING;

  -- Insert data into Domains table
  INSERT INTO domains (domain_id, tenant_id, domain_name, owner_user_id, description, created_at)
  VALUES
    (gen_random_uuid(), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'Sales', (SELECT user_id FROM users WHERE email = 'user1@example.com'), 'This is a Sales example domain', CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'IT', (SELECT user_id FROM users WHERE email = 'user2@example.com'), 'This is an IT domain', CURRENT_TIMESTAMP)
  ON CONFLICT (domain_id) DO NOTHING;

  -- Insert data into DomainVersions table and create corresponding graphs for Apache AGE
  INSERT INTO domain_versions (domain_id, tenant_id, version, graph_name, created_at)
  VALUES
    ((SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 1, 'Sales_v1', CURRENT_TIMESTAMP),
    ((SELECT domain_id FROM domains WHERE domain_name = 'IT'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 1, 'IT_v1', CURRENT_TIMESTAMP)
  ON CONFLICT (domain_id, version) DO NOTHING;

  -- Create graphs in Apache AGE for each domain version
  SELECT * FROM ag_catalog.create_graph('Sales_v1');
  SELECT * FROM ag_catalog.create_graph('IT_v1');

  -- SELECT * FROM create_graph('Sales_v1');
  -- SELECT * FROM create_graph('IT_v1');

  -- Assign 'owner' role to each domain owner for their own domain
  INSERT INTO user_roles (user_id, domain_id, role_id)
  SELECT owner_user_id, domain_id, (SELECT role_id FROM roles WHERE role_name = 'owner' AND tenant_id = domains.tenant_id LIMIT 1)
  FROM domains
  ON CONFLICT (user_id, domain_id) DO NOTHING;

  -- Assign 'member' role to user1 for the IT domain
  INSERT INTO user_roles (user_id, domain_id, role_id)
  VALUES
    ((SELECT user_id FROM users WHERE email = 'user1@example.com'), (SELECT domain_id FROM domains WHERE domain_name = 'IT'), (SELECT role_id FROM roles WHERE role_name = 'member' AND tenant_id = (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One') LIMIT 1))
  ON CONFLICT (user_id, domain_id) DO NOTHING;

  -- Assign 'Viewer' role to user2 for the Sales domain
  INSERT INTO user_roles (user_id, domain_id, role_id)
  VALUES
    ((SELECT user_id FROM users WHERE email = 'user2@example.com'), (SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT role_id FROM roles WHERE role_name = 'viewer' AND tenant_id = (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One') LIMIT 1))
  ON CONFLICT (user_id, domain_id) DO NOTHING;

  -- Insert user configuration settings for each user
  INSERT INTO user_config (config_id, user_id, tenant_id, config_key, config_value, created_at)
  VALUES
    (gen_random_uuid(), (SELECT user_id FROM users WHERE email = 'user1@example.com'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'theme', 'dark', CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT user_id FROM users WHERE email = 'user1@example.com'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'notifications', 'enabled', CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT user_id FROM users WHERE email = 'user2@example.com'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'theme', 'light', CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT user_id FROM users WHERE email = 'user2@example.com'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'notifications', 'disabled', CURRENT_TIMESTAMP)
  ON CONFLICT (config_id) DO NOTHING;

  -- Insert domain configuration settings for each domain
  INSERT INTO domain_config (config_id, domain_id, tenant_id, config_key, config_value, created_at)
  VALUES
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'default_language', 'en', CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'Sales'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'time_zone', 'UTC', CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'IT'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'default_language', 'es', CURRENT_TIMESTAMP),
    (gen_random_uuid(), (SELECT domain_id FROM domains WHERE domain_name = 'IT'), (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'), 'time_zone', 'CET', CURRENT_TIMESTAMP)
  ON CONFLICT (config_id) DO NOTHING;

  -- Insert entities into the entities table
  INSERT INTO entities (entity_id, name, description, entity_type, vector, meta_data, tenant_id, domain_id)
  VALUES
      (gen_random_uuid(), 'Sales', 'Main entity for the Sales domain', 'core', NULL, '{"source": "CRM"}', 
        (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'),
        (SELECT domain_id FROM domains WHERE domain_name = 'Sales')),
      (gen_random_uuid(), 'Total Sales', 'Total sales for a specific period', 'definition', NULL, '{"unit": "USD"}', 
        (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'),
        (SELECT domain_id FROM domains WHERE domain_name = 'Sales')),
      (gen_random_uuid(), 'Monthly Sales', 'Sales data for each month', 'definition', NULL, '{"frequency": "monthly"}', 
        (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'),
        (SELECT domain_id FROM domains WHERE domain_name = 'Sales')),
      (gen_random_uuid(), 'Quarterly Sales', 'Sales data for each quarter', 'definition', NULL, '{"frequency": "quarterly"}', 
        (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'),
        (SELECT domain_id FROM domains WHERE domain_name = 'Sales')),
      (gen_random_uuid(), 'Sales Forecast', 'Predicted future sales based on current trends', 'definition', NULL, '{"methodology": "statistical analysis"}', 
        (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'),
        (SELECT domain_id FROM domains WHERE domain_name = 'Sales')),
      (gen_random_uuid(), 'Customer Retention', 'The rate at which customers return to make purchases', 'definition', NULL, '{"metric": "retention rate"}', 
        (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'),
        (SELECT domain_id FROM domains WHERE domain_name = 'Sales'))
  ON CONFLICT (entity_id) DO NOTHING;

  -- Insert relationships into the relationships table
  INSERT INTO relationships (edge_id, relationship_type, description, vector, meta_data, tenant_id, domain_id, source_entity_id, target_entity_id)
  VALUES
      (gen_random_uuid(), 'is_part_of', 'Total sales is part of Sales', NULL, '{"importance": "high"}', 
        (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'),
        (SELECT domain_id FROM domains WHERE domain_name = 'Sales'),
        (SELECT entity_id FROM entities WHERE name = 'Sales'), (SELECT entity_id FROM entities WHERE name = 'Total Sales')),
      (gen_random_uuid(), 'is_part_of', 'Monthly sales is part of Sales', NULL, '{"importance": "medium"}', 
        (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'),
        (SELECT domain_id FROM domains WHERE domain_name = 'Sales'),
        (SELECT entity_id FROM entities WHERE name = 'Sales'), (SELECT entity_id FROM entities WHERE name = 'Monthly Sales')),
      (gen_random_uuid(), 'is_part_of', 'Quarterly sales is part of Sales', NULL, '{"importance": "medium"}', 
        (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'),
        (SELECT domain_id FROM domains WHERE domain_name = 'Sales'),
        (SELECT entity_id FROM entities WHERE name = 'Sales'), (SELECT entity_id FROM entities WHERE name = 'Quarterly Sales')),
      (gen_random_uuid(), 'is_part_of', 'Sales forecast is part of Sales', NULL, '{"importance": "low"}', 
        (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'),
        (SELECT domain_id FROM domains WHERE domain_name = 'Sales'),
        (SELECT entity_id FROM entities WHERE name = 'Sales'), (SELECT entity_id FROM entities WHERE name = 'Sales Forecast')),
      (gen_random_uuid(), 'is_part_of', 'Customer retention is part of Sales', NULL, '{"importance": "medium"}', 
        (SELECT tenant_id FROM tenants WHERE tenant_name = 'Tenant One'),
        (SELECT domain_id FROM domains WHERE domain_name = 'Sales'),
        (SELECT entity_id FROM entities WHERE name = 'Sales'), (SELECT entity_id FROM entities WHERE name = 'Customer Retention'))
  ON CONFLICT (edge_id) DO NOTHING;

  COMMIT;
EOSQL


echo "Inserting data into Apache AGE graphs..."

psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-'EOSQL'
  -- Enable error stopping
  \set ON_ERROR_STOP on

  -- Set search path for AGE graphs
  SET search_path = ag_catalog, public;

  -- Insert data into the Sales graph (Sales_v1)
  SELECT * FROM cypher('Sales_v1', $$

    CREATE 
      (s:Entity {name: 'Sales', description: 'Main entity for the Sales domain', entity_type: 'core'}),
      (ts:Entity {name: 'Total Sales', description: 'Total sales for a specific period', entity_type: 'definition'}),
      (ms:Entity {name: 'Monthly Sales', description: 'Sales data for each month', entity_type: 'definition'}),
      (qs:Entity {name: 'Quarterly Sales', description: 'Sales data for each quarter', entity_type: 'definition'}),
      (sf:Entity {name: 'Sales Forecast', description: 'Predicted future sales', entity_type: 'definition'}),
      (cr:Entity {name: 'Customer Retention', description: 'Rate of customer return', entity_type: 'definition'}),
      (ts)-[:IS_PART_OF]->(s),
      (ms)-[:IS_PART_OF]->(s),
      (qs)-[:IS_PART_OF]->(s),
      (sf)-[:IS_PART_OF]->(s),
      (cr)-[:IS_PART_OF]->(s)

  $$) AS t(c agtype);

EOSQL

if [ $? -eq 0 ]; then
  echo "Graph data inserted successfully."
else
  echo "Failed to insert graph data. Exiting..."
  exit 1
fi

