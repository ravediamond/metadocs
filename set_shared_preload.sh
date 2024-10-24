#!/bin/bash
# This script runs during the initialization of the PostgreSQL database.

# Append 'age' to shared_preload_libraries in postgresql.conf
echo "shared_preload_libraries = 'age'" >> "$PGDATA/postgresql.conf"

# Set AGE library path
# RUN echo "age.control" >> /var/lib/postgresql/data/extension/age.control

# Ensure extensions are created
# RUN echo "CREATE EXTENSION IF NOT EXISTS pgcrypto;" > /docker-entrypoint-initdb.d/init_extensions.sql
# RUN echo "CREATE EXTENSION IF NOT EXISTS age;" >> /docker-entrypoint-initdb.d/init_extensions.sql
# RUN echo "CREATE EXTENSION IF NOT EXISTS vector;" >> /docker-entrypoint-initdb.d/init_extensions.sql