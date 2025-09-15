#!/bin/bash
# deploy_functions.sh - Script to deploy custom functions

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

echo "Deploying custom functions..."

# Deploy functions
functions=(
    "$SCRIPT_DIR/functions/get_user_file_stats.sql"
    "$SCRIPT_DIR/functions/get_recent_qna.sql"
    "$SCRIPT_DIR/functions/get_user_profile.sql"
)

for function in "${functions[@]}"; do
    if [ -f "$function" ]; then
        echo "Deploying $function..."
        psql $DATABASE_URL -f "$function"
        if [ $? -ne 0 ]; then
            echo "Failed to deploy $function"
            exit 1
        fi
    else
        echo "Function file $function not found"
        exit 1
    fi
done

echo "All functions deployed successfully!"