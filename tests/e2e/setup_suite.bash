#!/bin/bash

# Test suite setup - creates a kind cluster with KubeVirt

set -euo pipefail

setup_suite() {
    # Clean environment
    unset KUBECONFIG || true
    unset GLOBAL_KUBECONFIG || true

    CLUSTER_NAME=kind

    # Check if kind cluster already exists
    if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
        echo "Kind cluster '${CLUSTER_NAME}' already exists, skipping creation..."
        kind get kubeconfig --name kind > kind-kubeconfig
        export KUBECONFIG=kind-kubeconfig
        echo "✅ Using existing cluster!"
        echo "KUBECONFIG=$(pwd)/kind-kubeconfig"
        return 0
    fi

    echo "Creating kind cluster..."
    cat <<EOF | kind create cluster \
      --name $CLUSTER_NAME           \
      -v7 --wait 1m --retain --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
networking:
  ipFamily: dual
nodes:
- role: control-plane
- role: worker
- role: worker
EOF

    echo "Setting up kubeconfig..."
    kind get kubeconfig --name kind > kind-kubeconfig
    export KUBECONFIG=kind-kubeconfig

    echo "Installing KubeVirt..."
    LATEST=$(curl -L "https://storage.googleapis.com/kubevirt-prow/devel/nightly/release/kubevirt/kubevirt/latest")
    kubectl apply -f "https://storage.googleapis.com/kubevirt-prow/devel/nightly/release/kubevirt/kubevirt/${LATEST}/kubevirt-operator.yaml"
    kubectl apply -f "https://storage.googleapis.com/kubevirt-prow/devel/nightly/release/kubevirt/kubevirt/${LATEST}/kubevirt-cr.yaml"
    kubectl wait -n kubevirt kv kubevirt --for condition=Available --timeout 15m

    echo "Installing Multus..."
    # vanilla manifests, just removed the limits
    kubectl create -f manifests/multus-daemonset-thick.yml
    kubectl wait --for=condition=ready pod -l app=multus -n kube-system --timeout=10m

    echo "Test suite setup complete!"
    echo "KUBECONFIG=$(pwd)/kind-kubeconfig"
}

teardown_suite() {
    # TODO: Implement cluster teardown
    echo "Teardown not implemented yet"
}
