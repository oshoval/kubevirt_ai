package main

import (
	"fmt"
	"os"
	"os/exec"
)

type ClusterInfo struct {
	Found      bool
	Kubeconfig string
	Message    string
}

func detectKubevirtciCluster() (string, error) {
	var kubeconfigPath string
	var source string

	// First, check if GLOBAL_KUBECONFIG environment variable is set
	globalKubeconfig := os.Getenv("GLOBAL_KUBECONFIG")

	if globalKubeconfig != "" {
		// Check if the GLOBAL_KUBECONFIG file exists
		if _, err := os.Stat(globalKubeconfig); err == nil {
			kubeconfigPath = globalKubeconfig
			source = "GLOBAL_KUBECONFIG"
		}
	}

	// If GLOBAL_KUBECONFIG not found, try ~/.kube/config
	if kubeconfigPath == "" {
		homeDir, err := os.UserHomeDir()
		if err == nil {
			defaultKubeconfig := homeDir + "/.kube/config"
			if _, err := os.Stat(defaultKubeconfig); err == nil {
				kubeconfigPath = defaultKubeconfig
				source = "~/.kube/config"
			}
		}
	}

	// If no kubeconfig found
	if kubeconfigPath == "" {
		return "No kubeconfig found. Checked GLOBAL_KUBECONFIG environment variable and ~/.kube/config", nil
	}

	// Test cluster connectivity using the kubeconfig
	clusterInfo := testClusterConnectivity(kubeconfigPath)

	if !clusterInfo.Found {
		return fmt.Sprintf("Cluster not accessible via %s (%s)\n%s", source, kubeconfigPath, clusterInfo.Message), nil
	}

	// Success - cluster is accessible
	result := fmt.Sprintf(`Cluster Available via %s

🔧 Setup Commands:
   export KUBECONFIG=%s

📝 Verification:
   kubectl get nodes
   kubectl get kubevirt -n kubevirt

✨ Ready to use cluster!`, source, kubeconfigPath)

	return result, nil
}

func testClusterConnectivity(kubeconfigPath string) ClusterInfo {
	info := ClusterInfo{
		Found:      false,
		Kubeconfig: kubeconfigPath,
	}

	// Test kubectl connectivity
	cmd := exec.Command("kubectl", "get", "nodes", "--kubeconfig", kubeconfigPath)
	output, err := cmd.CombinedOutput()

	if err != nil {
		info.Message = fmt.Sprintf("kubectl connectivity test failed: %v\nOutput: %s", err, string(output))
		return info
	}

	// If we get here, kubectl worked
	info.Found = true
	info.Message = "Cluster is accessible via kubectl"
	return info
}
