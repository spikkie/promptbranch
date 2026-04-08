#!/bin/bash

# === Configuration ===
REVISION_MSG="Add is_receipt field to receipts"
MIGRATIONS_DIR="/app/migrations/versions"
LOCAL_COPY_PATH="./migrations_downloaded" # On your host machine
DEV_USER="spikkie"                        # Will be used for chown later
DEV_GROUP="spikkie"                       # Optional, or same as DEV_USER
POD_NAME="your-pod-name"                  # e.g. bonnetjes-app-backend-xxx
NAMESPACE="default"                       # or your K8s namespace

# === 1. Generate migration ===
echo "📦 Generating Alembic migration..."
alembic revision --autogenerate -m "$REVISION_MSG"

# === 2. Find latest migration file ===
LATEST_FILE=$(ls -t "$MIGRATIONS_DIR" | head -n 1)
FULL_POD_PATH="$MIGRATIONS_DIR/$LATEST_FILE"

# === 3. Change permissions inside the pod ===
echo "🔧 Setting file permissions..."
chmod 644 "$FULL_POD_PATH"
chown $DEV_USER:$DEV_GROUP "$FULL_POD_PATH"

# === 4. Copy to local machine using kubectl ===
echo "⬇️ Copying file from pod to local..."
kubectl cp "$POD_NAME:$FULL_POD_PATH" "$LOCAL_COPY_PATH/$LATEST_FILE" -n "$NAMESPACE"

# === 5. Done ===
echo "✅ Migration script copied to $LOCAL_COPY_PATH/$LATEST_FILE"
