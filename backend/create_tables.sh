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

  ALTER DATABASE db SET search_path = public, ag_catalog;

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

  -- SET search_path = public, ag_catalog;

  BEGIN;

  -- Insert data into Tenants table with fixed UUID
  INSERT INTO tenants (tenant_id, tenant_name)
  VALUES
    ('11111111-1111-1111-1111-111111111111', 'Tenant One')
  ON CONFLICT (tenant_id) DO NOTHING;

  -- Insert data into Users table with fixed UUIDs
  INSERT INTO users (user_id, email, hashed_password, name)
  VALUES
    ('22222222-2222-2222-2222-222222222222', 'user1@example.com', '$2b$12$ctUeogp4nb3cbMERRe1qVeRfgh3aIxP7clgEPgu1A.JrUOv6apnT2', 'User One'),
    ('33333333-3333-3333-3333-333333333333', 'user2@example.com', '$2b$12$RaerUrFIbqkUomI.4YWnROJ419pK2h8Fbs/4bIBlaviSzKoXwutJK', 'User Two')
  ON CONFLICT (user_id) DO NOTHING;

  -- Insert default roles into the Roles table with fixed UUIDs
  INSERT INTO roles (role_id, tenant_id, role_name, description)
  VALUES
    ('44444444-4444-4444-4444-444444444444', '11111111-1111-1111-1111-111111111111', 'owner', 'Full access to the domain, including managing roles'),
    ('55555555-5555-5555-5555-555555555555', '11111111-1111-1111-1111-111111111111', 'admin', 'Administrative access to the domain'),
    ('66666666-6666-6666-6666-666666666666', '11111111-1111-1111-1111-111111111111', 'member', 'Can contribute to the domain'),
    ('77777777-7777-7777-7777-777777777777', '11111111-1111-1111-1111-111111111111', 'viewer', 'Can view domain content')
  ON CONFLICT (tenant_id, role_name) DO NOTHING;

  -- Associate users with the tenant and assign roles
  INSERT INTO user_tenants (user_id, tenant_id, role_id)
  VALUES
    ('22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', '44444444-4444-4444-4444-444444444444'),  -- User One as owner
    ('33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', '66666666-6666-6666-6666-666666666666')   -- User Two as member
  ON CONFLICT (user_id, tenant_id) DO NOTHING;

  -- Insert data into Domains table with fixed UUIDs
  INSERT INTO domains (domain_id, tenant_id, domain_name, owner_user_id, description, created_at)
  VALUES
    ('88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'Sales', '22222222-2222-2222-2222-222222222222', 'This is a Sales example domain', CURRENT_TIMESTAMP),
    ('99999999-9999-9999-9999-999999999999', '11111111-1111-1111-1111-111111111111', 'IT', '33333333-3333-3333-3333-333333333333', 'This is an IT domain', CURRENT_TIMESTAMP)
  ON CONFLICT (domain_id) DO NOTHING;

  -- Insert data into DomainVersions table with fixed UUIDs and graph names
  INSERT INTO domain_versions (domain_id, tenant_id, version, graph_name, created_at)
  VALUES
    ('88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 1, 'Sales_v1', CURRENT_TIMESTAMP),
    ('99999999-9999-9999-9999-999999999999', '11111111-1111-1111-1111-111111111111', 1, 'IT_v1', CURRENT_TIMESTAMP)
  ON CONFLICT (domain_id, version) DO NOTHING;

  -- Create graphs in Apache AGE for each domain version
  SELECT * FROM ag_catalog.create_graph('Sales_v1');
  SELECT * FROM ag_catalog.create_graph('IT_v1');

  -- Assign 'owner' role to each domain owner for their own domain
  INSERT INTO user_roles (user_id, domain_id, role_id)
  SELECT owner_user_id, domain_id, '44444444-4444-4444-4444-444444444444'
  FROM domains
  ON CONFLICT (user_id, domain_id) DO NOTHING;

  -- Assign 'member' role to user1 for the IT domain
  INSERT INTO user_roles (user_id, domain_id, role_id)
  VALUES
    ('22222222-2222-2222-2222-222222222222', '99999999-9999-9999-9999-999999999999', '66666666-6666-6666-6666-666666666666')
  ON CONFLICT (user_id, domain_id) DO NOTHING;

  -- Assign 'viewer' role to user2 for the Sales domain
  INSERT INTO user_roles (user_id, domain_id, role_id)
  VALUES
    ('33333333-3333-3333-3333-333333333333', '88888888-8888-8888-8888-888888888888', '77777777-7777-7777-7777-777777777777')
  ON CONFLICT (user_id, domain_id) DO NOTHING;

  -- Insert user configuration settings for each user
  INSERT INTO user_config (config_id, user_id, tenant_id, config_key, config_value, created_at)
  VALUES
    (gen_random_uuid(), '22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 'theme', 'dark', CURRENT_TIMESTAMP),
    (gen_random_uuid(), '22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 'notifications', 'enabled', CURRENT_TIMESTAMP),
    (gen_random_uuid(), '33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', 'theme', 'light', CURRENT_TIMESTAMP),
    (gen_random_uuid(), '33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', 'notifications', 'disabled', CURRENT_TIMESTAMP)
  ON CONFLICT (config_id) DO NOTHING;

  -- Insert domain configuration settings for each domain
  INSERT INTO domain_config (config_id, domain_id, tenant_id, config_key, config_value, created_at)
  VALUES
    (gen_random_uuid(), '88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'default_language', 'en', CURRENT_TIMESTAMP),
    (gen_random_uuid(), '88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'time_zone', 'UTC', CURRENT_TIMESTAMP),
    (gen_random_uuid(), '99999999-9999-9999-9999-999999999999', '11111111-1111-1111-1111-111111111111', 'default_language', 'es', CURRENT_TIMESTAMP),
    (gen_random_uuid(), '99999999-9999-9999-9999-999999999999', '11111111-1111-1111-1111-111111111111', 'time_zone', 'CET', CURRENT_TIMESTAMP)
  ON CONFLICT (config_id) DO NOTHING;

  COMMIT;
EOSQL

if [ $? -eq 0 ]; then
  echo "Initial data inserted successfully."
else
  echo "Failed to insert initial data. Exiting..."
  exit 1
fi

echo "Inserting data into Apache AGE graphs with internal node identifiers..."

# Function to insert graph data with internal node identifiers
insert_graph_data() {
  GRAPH_NAME=$1
  shift

  psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-EOSQL
    -- Enable error stopping
    \set ON_ERROR_STOP on

    -- Insert entities into the ${GRAPH_NAME} graph and return their internal ids
    SELECT * FROM cypher('${GRAPH_NAME}', \$CYPHER\$
      CREATE 
        (e1:Entity { 
          name: 'Sales',
          type: 'Department',
          description: 'Handles all sales operations',
          metadata: '{"location": "Building A", "budget": 100000}',
          vector: [0.1, 0.2, 0.3, 0.4],
          created_at: '2024-04-17T12:00:00Z'
        }),
        (e2:Entity { 
          name: 'Total Sales',
          type: 'Metric',
          description: 'Aggregated total sales figures',
          metadata: '{"unit": "USD"}',
          vector: [0.2, 0.3, 0.4, 0.5],
          created_at: '2024-04-17T12:05:00Z'
        }),
        (e3:Entity { 
          name: 'Monthly Sales',
          type: 'Metric',
          description: 'Monthly sales figures',
          metadata: '{"unit": "USD"}',
          vector: [0.3, 0.4, 0.5, 0.6],
          created_at: '2024-04-17T12:10:00Z'
        }),
        (e4:Entity { 
          name: 'Quarterly Sales',
          type: 'Metric',
          description: 'Quarterly sales figures',
          metadata: '{"unit": "USD"}',
          vector: [0.4, 0.5, 0.6, 0.7],
          created_at: '2024-04-17T12:15:00Z'
        }),
        (e5:Entity { 
          name: 'Sales Forecast',
          type: 'Projection',
          description: 'Forecasted sales figures for the next quarter',
          metadata: '{"confidence_level": "high"}',
          vector: [0.5, 0.6, 0.7, 0.8],
          created_at: '2024-04-17T12:20:00Z'
        }),
        (e6:Entity { 
          name: 'Customer Retention',
          type: 'Metric',
          description: 'Measures the ability to retain customers',
          metadata: '{"target": "90%"}',
          vector: [0.6, 0.7, 0.8, 0.9],
          created_at: '2024-04-17T12:25:00Z'
        })
      RETURN id(e1) AS entity1_id, id(e2) AS entity2_id, id(e3) AS entity3_id, 
             id(e4) AS entity4_id, id(e5) AS entity5_id, id(e6) AS entity6_id
    \$CYPHER\$) AS t(entity1_id agtype, entity2_id agtype, entity3_id agtype, 
                    entity4_id agtype, entity5_id agtype, entity6_id agtype);
EOSQL

    # Capture the internal node IDs from the output
    ENTITY_IDS=$(psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "
      SELECT entity1_id, entity2_id, entity3_id, entity4_id, entity5_id, entity6_id
      FROM cypher('${GRAPH_NAME}', \$CYPHER\$
        MATCH (e1:Entity {name: 'Sales'}),
              (e2:Entity {name: 'Total Sales'}),
              (e3:Entity {name: 'Monthly Sales'}),
              (e4:Entity {name: 'Quarterly Sales'}),
              (e5:Entity {name: 'Sales Forecast'}),
              (e6:Entity {name: 'Customer Retention'})
        RETURN id(e1), id(e2), id(e3), id(e4), id(e5), id(e6)
      \$CYPHER\$) AS t(entity1_id agtype, entity2_id agtype, entity3_id agtype, entity4_id agtype, entity5_id agtype, entity6_id agtype);
    ")

    # Split the ENTITY_IDS into individual variables
    ENTITY1_ID=$(echo $ENTITY_IDS | cut -d'|' -f1)
    ENTITY2_ID=$(echo $ENTITY_IDS | cut -d'|' -f2)
    ENTITY3_ID=$(echo $ENTITY_IDS | cut -d'|' -f3)
    ENTITY4_ID=$(echo $ENTITY_IDS | cut -d'|' -f4)
    ENTITY5_ID=$(echo $ENTITY_IDS | cut -d'|' -f5)
    ENTITY6_ID=$(echo $ENTITY_IDS | cut -d'|' -f6)

    # Insert relationships using the internal node IDs
    psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-EOSQL
      -- Insert relationships into the ${GRAPH_NAME} graph with internal node ids
      SELECT * FROM cypher('${GRAPH_NAME}', \$CYPHER\$
        MATCH 
          (a:Entity), 
          (b:Entity),
          (c:Entity),
          (d:Entity),
          (e:Entity),
          (f:Entity)
        WHERE id(a) = ${ENTITY1_ID} AND id(b) = ${ENTITY2_ID} 
              AND id(c) = ${ENTITY3_ID} AND id(d) = ${ENTITY4_ID}
              AND id(e) = ${ENTITY5_ID} AND id(f) = ${ENTITY6_ID}
        CREATE 
          (b)-[:Relationship { 
            name: 'Aggregates',
            type: 'Aggregation',
            description: 'Total Sales aggregates various sales metrics',
            metadata: '{"frequency": "monthly"}',
            vector: [0.1, 0.1, 0.1, 0.1],
            created_at: '2024-04-17T12:30:00Z'
          }]->(a),
          (c)-[:Relationship { 
            name: 'Tracks',
            type: 'Tracking',
            description: 'Monthly Sales tracks sales on a monthly basis',
            metadata: '{"frequency": "monthly"}',
            vector: [0.2, 0.2, 0.2, 0.2],
            created_at: '2024-04-17T12:35:00Z'
          }]->(a),
          (d)-[:Relationship { 
            name: 'Tracks',
            type: 'Tracking',
            description: 'Quarterly Sales tracks sales on a quarterly basis',
            metadata: '{"frequency": "quarterly"}',
            vector: [0.3, 0.3, 0.3, 0.3],
            created_at: '2024-04-17T12:40:00Z'
          }]->(a),
          (e)-[:Relationship { 
            name: 'Projects',
            type: 'Projection',
            description: 'Sales Forecast projects future sales figures',
            metadata: '{"model": "linear regression"}',
            vector: [0.4, 0.4, 0.4, 0.4],
            created_at: '2024-04-17T12:45:00Z'
          }]->(a),
          (f)-[:Relationship { 
            name: 'Measures',
            type: 'Measurement',
            description: 'Customer Retention measures the ability to retain customers',
            metadata: '{"target": "90%"}',
            vector: [0.5, 0.5, 0.5, 0.5],
            created_at: '2024-04-17T12:50:00Z'
          }]->(a)
      \$CYPHER\$) AS t(c agtype);
EOSQL

    if [ $? -eq 0 ]; then
      echo "Graph data with internal identifiers inserted successfully into ${GRAPH_NAME}."
    else
      echo "Failed to insert graph data into ${GRAPH_NAME}. Exiting..."
      exit 1
    fi
}

# Insert data into 'Sales_v1' graph
insert_graph_data "Sales_v1"