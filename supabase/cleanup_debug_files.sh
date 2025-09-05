#!/bin/bash

# Script to remove debug/development files (no longer needed as we have a clean migrations directory)
echo "Debug files have already been removed. The migrations directory now contains only the consolidated files:"
echo "1. 001_core_schema.sql"
echo "2. 002_rls_policies.sql"
echo "3. 003_functions.sql"
echo "4. 004_auth_hook.sql"
echo "5. schema.sql"