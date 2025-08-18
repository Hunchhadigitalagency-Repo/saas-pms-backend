#!/bin/sh

# Wait for PostgreSQL to be ready
until pg_isready -h db -p 5432 -U "$DB_USER"; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done

# Run database migrations
python manage.py migrate

# Apply tenant-specific migrations
python manage.py migrate_schemas --shared
python manage.py migrate_schemas --tenant

# Start Daphne
exec daphne -b 0.0.0.0 -p 8001 pms.asgi:application
