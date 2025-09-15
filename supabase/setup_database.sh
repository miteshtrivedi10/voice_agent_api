#!/bin/bash
# setup_database.sh - Comprehensive script to set up the entire database

# Check if psql is available
if ! command -v psql &> /dev/null
then
    echo "psql could not be found. Please install PostgreSQL client tools."
    exit 1
fi

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "DATABASE_URL environment variable is not set."
    echo "Please set it to your Supabase database connection string."
    echo "Example: export DATABASE_URL='postgresql://user:password@host:port/database'"
    exit 1
fi

echo "Setting up database..."

# Apply migrations
echo "Applying migrations..."
./apply_migrations.sh
if [ $? -ne 0 ]; then
    echo "Failed to apply migrations"
    exit 1
fi

# Deploy functions
echo "Deploying functions..."
./deploy_functions.sh
if [ $? -ne 0 ]; then
    echo "Failed to deploy functions"
    exit 1
fi

# Run tests
echo "Running tests..."
psql $DATABASE_URL -f tests/test_setup.sql
if [ $? -ne 0 ]; then
    echo "Tests failed"
    exit 1
fi

echo "Database setup completed successfully!"

echo ""
echo "Next steps:"
echo "1. Configure OAuth providers through the Supabase dashboard (see oauth_setup_guide.md)"
echo "2. Update your .env file with the necessary environment variables"
echo "3. Test the authentication flow in your application"