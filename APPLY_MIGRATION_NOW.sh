#!/bin/bash
# Скрипт для применения миграции на Railway

echo "🚀 Applying migration to Railway PostgreSQL..."
echo ""
echo "Step 1: Login to Railway"
railway login

echo ""
echo "Step 2: Link to project"
railway link -p 101cc62f-b314-41d1-9b55-d58ae5c371ea

echo ""
echo "Step 3: Apply migration"
cat apply_migration.sql | railway run psql $DATABASE_URL

echo ""
echo "✅ Done! Check the status at: https://vs5-production.up.railway.app/config"

