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

  CREATE EXTENSION IF NOT EXISTS pgcrypto;

  CREATE TABLE tenants (
      tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_name VARCHAR(255) NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE users (
      user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      email VARCHAR(255) UNIQUE NOT NULL,
      hashed_password TEXT NOT NULL,
      name VARCHAR(255) NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE domains (
      domain_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
      domain_name VARCHAR(255) NOT NULL,
      owner_user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
      description TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE roles (
      role_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
      role_name VARCHAR(50) NOT NULL,
      description TEXT,
      UNIQUE (tenant_id, role_name)
  );

  CREATE TABLE user_config (
      config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
      tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
      config_key VARCHAR(255) NOT NULL,
      config_value TEXT NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE domain_config (
      config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
      tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
      config_key VARCHAR(255) NOT NULL,
      config_value TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE api_keys (
      api_key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      api_key VARCHAR(64) UNIQUE NOT NULL,
      user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
      tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      revoked TIMESTAMP
  );

  CREATE TABLE user_roles (
      user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
      domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
      role_id UUID REFERENCES roles(role_id) ON DELETE CASCADE,
      tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (user_id, domain_id)
  );

  CREATE TABLE user_tenants (
      user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
      tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
      role_id UUID REFERENCES roles(role_id) ON DELETE CASCADE,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (user_id, tenant_id)
  );

  CREATE TABLE invitations (
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

  CREATE TABLE processing_pipeline (
    pipeline_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE NOT NULL,
    current_parse_id UUID,
    current_extract_id UUID,
    current_merge_id UUID,
    current_group_id UUID,
    current_ontology_id UUID,
    current_graph_id UUID,
    status VARCHAR(50),
    error VARCHAR(1024),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

CREATE TABLE files (
    file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE NOT NULL,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size BIGINT NOT NULL,
    original_path VARCHAR(1024) NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uploaded_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE file_versions (
    file_version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID REFERENCES files(file_id) ON DELETE CASCADE NOT NULL,
    version INT NOT NULL,
    filepath VARCHAR(1024) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE domain_version_files (
    domain_id UUID,
    domain_version INT,
    file_version_id UUID REFERENCES file_versions(file_version_id) ON DELETE CASCADE,
    status VARCHAR(50),
    error VARCHAR(1024),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (domain_id, domain_version) REFERENCES domain_versions(domain_id, version) ON DELETE CASCADE,
    PRIMARY KEY (domain_id, domain_version, file_version_id)
);

  -- Create enum type for domain version status
  CREATE TYPE domain_version_status AS ENUM (
      'DRAFT',
      'TO_BE_VALIDATED',
      'PUBLISHED',
      'PENDING_SUSPENSION',
      'SUSPENDED',
      'PENDING_DELETE',
      'DELETED'
  );

  CREATE TABLE domain_versions (
      domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
      tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE NOT NULL,
      version INT NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      status domain_version_status NOT NULL DEFAULT 'DRAFT',
      pipeline_id UUID REFERENCES processing_pipeline(pipeline_id),
      PRIMARY KEY (domain_id, version)
  );

  CREATE TABLE parse_versions (
      version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      pipeline_id UUID REFERENCES processing_pipeline(pipeline_id) ON DELETE CASCADE NOT NULL,
      version_number INTEGER NOT NULL,
      base_prompt TEXT NOT NULL,
      file_versions_id UUID[] NOT NULL,
      custom_instructions TEXT[] NOT NULL,
      file_statuses VARCHAR(50)[] NOT NULL,
      output_paths VARCHAR(1024)[] NOT NULL,
      errors VARCHAR(1024)[],
      global_status VARCHAR(50) NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE extract_versions (
      version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      pipeline_id UUID REFERENCES processing_pipeline(pipeline_id) ON DELETE CASCADE NOT NULL,
      version_number INTEGER NOT NULL,
      base_prompt TEXT NOT NULL,
      file_versions_id UUID[] NOT NULL,
      custom_instructions TEXT[] NOT NULL,
      file_statuses VARCHAR(50)[] NOT NULL,
      output_paths VARCHAR(1024)[] NOT NULL,
      errors VARCHAR(1024)[],
      global_status VARCHAR(50) NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE merge_versions (
      version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      pipeline_id UUID REFERENCES processing_pipeline(pipeline_id) ON DELETE CASCADE NOT NULL,
      version_number INTEGER NOT NULL,
      base_prompt TEXT NOT NULL,
      input_path VARCHAR(1024),
      output_path VARCHAR(1024),
      status VARCHAR(50),
      error VARCHAR(1024),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE group_versions (
      version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      pipeline_id UUID REFERENCES processing_pipeline(pipeline_id) ON DELETE CASCADE NOT NULL,
      version_number INTEGER NOT NULL,
      base_prompt TEXT NOT NULL,
      input_path VARCHAR(1024),
      output_path VARCHAR(1024),
      status VARCHAR(50),
      error VARCHAR(1024),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE ontology_versions (
      version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      pipeline_id UUID REFERENCES processing_pipeline(pipeline_id) ON DELETE CASCADE NOT NULL,
      version_number INTEGER NOT NULL,
      base_prompt TEXT NOT NULL,
      input_path VARCHAR(1024),
      output_path VARCHAR(1024),
      status VARCHAR(50),
      error VARCHAR(1024),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE graph_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID REFERENCES processing_pipeline(pipeline_id) ON DELETE CASCADE NOT NULL,
    version_number INTEGER NOT NULL,
    base_prompt TEXT NOT NULL,
    input_path VARCHAR(1024),
    output_path VARCHAR(1024),
    status VARCHAR(50),
    error VARCHAR(1024),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

  -- Indexes
  CREATE INDEX idx_files_domain_id ON files(domain_id);
  CREATE INDEX idx_files_processing_status ON files(processing_status);
  CREATE INDEX idx_email ON users(email);
  CREATE INDEX idx_invitee_email ON invitations(invitee_email);
  CREATE INDEX idx_tenant_id ON invitations(tenant_id);
  CREATE INDEX idx_pipeline_domain ON processing_pipeline(domain_id);
  CREATE INDEX idx_pipeline_status ON processing_pipeline(status);
  CREATE INDEX idx_parse_versions_pipeline ON parse_versions(pipeline_id);
  CREATE INDEX idx_extract_versions_pipeline ON extract_versions(pipeline_id);
  CREATE INDEX idx_merge_versions_pipeline ON merge_versions(pipeline_id);
  CREATE INDEX idx_group_versions_pipeline ON group_versions(pipeline_id);
  CREATE INDEX idx_ontology_versions_pipeline ON ontology_versions(pipeline_id);
  CREATE INDEX idx_graph_versions_pipeline ON graph_versions(pipeline_id);

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

  INSERT INTO tenants (tenant_id, tenant_name) VALUES
  ('11111111-1111-1111-1111-111111111111', 'Tenant One');

  INSERT INTO users (user_id, email, hashed_password, name) VALUES
  ('22222222-2222-2222-2222-222222222222', 'user1@example.com', '$2b$12$ctUeogp4nb3cbMERRe1qVeRfgh3aIxP7clgEPgu1A.JrUOv6apnT2', 'User One'),
  ('33333333-3333-3333-3333-333333333333', 'user2@example.com', '$2b$12$RaerUrFIbqkUomI.4YWnROJ419pK2h8Fbs/4bIBlaviSzKoXwutJK', 'User Two');

  INSERT INTO roles (role_id, tenant_id, role_name, description) VALUES
  ('44444444-4444-4444-4444-444444444444', '11111111-1111-1111-1111-111111111111', 'owner', 'Full access to the domain, including managing roles'),
  ('55555555-5555-5555-5555-555555555555', '11111111-1111-1111-1111-111111111111', 'admin', 'Administrative access to the domain'),
  ('66666666-6666-6666-6666-666666666666', '11111111-1111-1111-1111-111111111111', 'member', 'Can contribute to the domain'),
  ('77777777-7777-7777-7777-777777777777', '11111111-1111-1111-1111-111111111111', 'viewer', 'Can view domain content');

  INSERT INTO domains (domain_id, tenant_id, domain_name, owner_user_id, description) VALUES
  ('88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'Sales', '22222222-2222-2222-2222-222222222222', 'This is a Sales example domain');

  INSERT INTO user_tenants (user_id, tenant_id, role_id) VALUES
  ('22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', '44444444-4444-4444-4444-444444444444'),
  ('33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', '66666666-6666-6666-6666-666666666666');

  INSERT INTO user_roles (user_id, domain_id, role_id, tenant_id) VALUES
  (
      '22222222-2222-2222-2222-222222222222',
      '88888888-8888-8888-8888-888888888888',
      '44444444-4444-4444-4444-444444444444',
      '11111111-1111-1111-1111-111111111111'
  ),
  (
      '33333333-3333-3333-3333-333333333333',
      '88888888-8888-8888-8888-888888888888',
      '66666666-6666-6666-6666-666666666666',
      '11111111-1111-1111-1111-111111111111'
  );

  INSERT INTO user_config (user_id, tenant_id, config_key, config_value) VALUES
  ('22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 'theme', 'dark'),
  ('22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 'notifications', 'enabled'),
  ('33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', 'theme', 'light'),
  ('33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', 'notifications', 'disabled');

  INSERT INTO domain_config (domain_id, tenant_id, config_key, config_value) VALUES
  ('88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'processing_dir', 'processing_output'),
  ('88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'processing_timeout', '3600'),
  ('88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'processing_batch_size', '5'),
  ('88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'pdf_quality_threshold', '75.0'),
  ('88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'pdf_max_iterations', '3'),
  ('88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'entity_max_iterations', '3'),
  ('88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'entity_batch_size', '5'),
  ('88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'aws_region', 'us-east-1'),
  ('88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'aws_model_id', 'us.anthropic.claude-3-5-sonnet-20241022-v2:0'),
  ('88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'llm_provider', 'bedrock'),
  ('88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'aws_profile', ''),
  ('88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'anthropic_api_key', ''),
  ('88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'llm_temperature', '0'),
  ('88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'llm_max_tokens', '4096');

  INSERT INTO domain_config (domain_id, tenant_id, config_key, config_value) VALUES
  ('88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'default_language', 'en'),
  ('88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', 'time_zone', 'UTC');

  COMMIT;
EOSQL

if [ $? -eq 0 ]; then
  echo "Initial data inserted successfully."
else
  echo "Failed to insert initial data. Exiting..."
  exit 1
fi
