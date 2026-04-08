#!/usr/bin/env bash

# Namespace
NAMESPACE="bonnetjes-app-backend"

# Find the pod name matching "bonnetjes-app-backend" but excluding "-postgresql-"
POD_NAME=$(microk8s kubectl get pods -n $NAMESPACE -o name | grep "pod/bonnetjes-app-backend" | grep -v "postgresql")

# Start exec bash on pod
echo "Start exec bash on $POD_NAME"
microk8s kubectl exec -it $POD_NAME -n $NAMESPACE -- bash
