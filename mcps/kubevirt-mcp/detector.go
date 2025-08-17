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
	// Check if GLOBAL_KUBECONFIG environment variable is set
	globalKubeconfig := os.Getenv("GLOBAL_KUBECONFIG")

	if globalKubeconfig == "" {
		return "GLOBAL_KUBECONFIG environment variable is not set", nil
	}

	// Check if the kubeconfig file exists
	if _, err := os.Stat(globalKubeconfig); os.IsNotExist(err) {
		return fmt.Sprintf("GLOBAL_KUBECONFIG file does not exist: %s", globalKubeconfig), nil
	}

	// Test cluster connectivity using the kubeconfig
	clusterInfo := testClusterConnectivity(globalKubeconfig)

	if !clusterInfo.Found {
		return fmt.Sprintf("Cluster not accessible via GLOBAL_KUBECONFIG\n%s", clusterInfo.Message), nil
	}

	// Success - cluster is accessible
	result := fmt.Sprintf(`Cluster Available via GLOBAL_KUBECONFIG

🔧 Setup Commands:
   export KUBECONFIG=%s

📝 Verification:
   kubectl get nodes
   kubectl get kubevirt -n kubevirt

✨ Ready to use cluster!`, globalKubeconfig)

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
