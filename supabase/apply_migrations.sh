#!/bin/bash
# apply_migrations.sh - Script to apply all migrations in order

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

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Applying migrations..."

# Apply migrations in order
migrations=(
    "$SCRIPT_DIR/migrations/20250915000000_create_file_details_table.sql"
    "$SCRIPT_DIR/migrations/20250915000001_create_question_and_answers_table.sql"
    "$SCRIPT_DIR/migrations/20250915000002_setup_security.sql"
    "$SCRIPT_DIR/migrations/20250915000003_add_processed_timestamp_trigger.sql"
    "$SCRIPT_DIR/migrations/20250915000004_setup_oauth_and_auth.sql"
    "$SCRIPT_DIR/migrations/20250915000005_add_file_alias_column.sql"
)

for migration in "${migrations[@]}"; do
    if [ -f "$migration" ]; then
        echo "Applying $migration..."
        psql $DATABASE_URL -f "$migration"
        if [ $? -ne 0 ]; then
            echo "Failed to apply $migration"
            exit 1
        fi
    else
        echo "Migration file $migration not found"
        exit 1
    fi
done

echo "All migrations applied successfully!"