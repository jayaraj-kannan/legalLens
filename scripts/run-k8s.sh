#!/usr/bin/env bash
set -e

# Ensure Docker Desktop binaries are in PATH
export PATH="$HOME/.docker/bin:/usr/local/bin:$PATH"

# LegalLens - Kubernetes Deployment Script
echo "======================================================"
echo "⚖️  LegalLens - Kubernetes Cluster Deployment"
echo "======================================================"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# 1. Check kubectl installation
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl CLI not found. Please install kubectl."
    echo "   macOS Install: brew install kubectl"
    exit 1
fi

# Check cluster connectivity
echo "🔍 Checking Kubernetes cluster connectivity..."
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster."
    echo "   Make sure your local cluster (Minikube, Kind, Docker Desktop, or K3s) is running."
    exit 1
fi

CURRENT_CONTEXT="$(kubectl config current-context)"
echo "✅ Connected to cluster context: $CURRENT_CONTEXT"

# 2. Build local Docker images if Docker is present
if command -v docker &> /dev/null && docker info &> /dev/null; then
    echo "🔨 Building Docker images locally..."
    docker build -t legallens-agent:latest ./agent
    docker build -t legallens-backend:latest ./backend
    docker build -t legallens-frontend:latest ./frontend

    # Kind image loading
    if [[ "$CURRENT_CONTEXT" == kind-* ]] && command -v kind &> /dev/null; then
        KIND_CLUSTER_NAME="${CURRENT_CONTEXT#kind-}"
        echo "📦 Sideloading images into Kind cluster '$KIND_CLUSTER_NAME'..."
        kind load docker-image legallens-agent:latest --name "$KIND_CLUSTER_NAME"
        kind load docker-image legallens-backend:latest --name "$KIND_CLUSTER_NAME"
        kind load docker-image legallens-frontend:latest --name "$KIND_CLUSTER_NAME"
    # Minikube image loading
    elif [[ "$CURRENT_CONTEXT" == "minikube" ]] && command -v minikube &> /dev/null; then
        echo "📦 Sideloading images into Minikube cluster..."
        minikube image load legallens-agent:latest
        minikube image load legallens-backend:latest
        minikube image load legallens-frontend:latest
    fi
fi

# 3. Create Namespace
echo "📁 Ensuring namespace 'legallens' exists..."
kubectl apply -f k8s/namespace.yaml

# 4. Provision GCP credentials Secret
ADC_PATH="${HOME}/.config/gcloud/application_default_credentials.json"
if [ -f "$ADC_PATH" ]; then
    echo "🔑 Configuring 'gcp-credentials' secret from ADC credentials..."
    kubectl create secret generic gcp-credentials \
        --namespace legallens \
        --from-file=key.json="$ADC_PATH" \
        --dry-run=client -o yaml | kubectl apply -f -
else
    echo "⚠️  No ADC file detected. Using fallback placeholder secret..."
    kubectl apply -f k8s/secret.yaml.template
fi

# 5. Apply All Manifests
echo "🚀 Applying Kubernetes resources (ConfigMap, Deployments, Services, Ingress)..."
kubectl apply -k k8s/

# 6. Wait for Rollouts
echo "⏳ Waiting for deployments to become ready..."
kubectl rollout status deployment/legallens-agent -n legallens --timeout=120s || true
kubectl rollout status deployment/legallens-backend -n legallens --timeout=120s || true
kubectl rollout status deployment/legallens-frontend -n legallens --timeout=120s || true

echo ""
echo "======================================================"
echo "🎉 LegalLens Kubernetes Pods & Services"
echo "======================================================"
kubectl get all -n legallens

echo ""
echo "======================================================"
echo "🌐 Accessing the Application"
echo "======================================================"
echo "1. Port-Forward Frontend to your browser:"
echo "   kubectl port-forward svc/legallens-frontend 3000:80 -n legallens"
echo "   Open: http://localhost:3000"
echo ""
echo "2. Port-Forward Backend directly (optional):"
echo "   kubectl port-forward svc/legallens-backend 8080:8080 -n legallens"
echo "   Open API docs: http://localhost:8080/docs"
echo ""
echo "3. Stream Pod Logs:"
echo "   kubectl logs -f -l app=legallens-backend -n legallens"
echo "   kubectl logs -f -l app=legallens-agent -n legallens"
echo "======================================================"
