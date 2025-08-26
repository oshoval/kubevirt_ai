package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
)

type ClusterInfo struct {
	Found      bool
	Kubeconfig string
	Message    string
}

func detectKubevirtciCluster() (string, error) {
	var kubeconfigPath string
	var source string

	// First, check if KUBECONFIG environment variable is already set
	existingKubeconfig := os.Getenv("KUBECONFIG")
	if existingKubeconfig != "" {
		if _, err := os.Stat(existingKubeconfig); err == nil {
			kubeconfigPath = existingKubeconfig
			source = "KUBECONFIG environment variable"
		}
	}

	// Second, check if we can use in-cluster authentication (running in a pod)
	if kubeconfigPath == "" {
		clusterInfo := testInClusterConnectivity()
		if clusterInfo.Found {
			result := `Cluster Available via in-cluster authentication

🔧 Environment: Running inside Kubernetes pod
   ✅ Service account authentication active
   ✅ No kubeconfig configuration needed

📝 Verification:
   kubectl get nodes
   kubectl get kubevirt -n kubevirt

✨ Ready to use cluster!`
			return result, nil
		}
	}

	// Third, check if GLOBAL_KUBECONFIG environment variable is set
	if kubeconfigPath == "" {
		globalKubeconfig := os.Getenv("GLOBAL_KUBECONFIG")
		if globalKubeconfig != "" {
			// Check if the GLOBAL_KUBECONFIG file exists
			if _, err := os.Stat(globalKubeconfig); err == nil {
				kubeconfigPath = globalKubeconfig
				source = "GLOBAL_KUBECONFIG"
			}
		}
	}

	// Fourth, try ~/.kube/config
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
		return "No kubeconfig found. Checked KUBECONFIG, GLOBAL_KUBECONFIG environment variables, ~/.kube/config, and in-cluster authentication", nil
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

// testInClusterConnectivity tests cluster connectivity using in-cluster authentication
// This approach is simpler and more reliable than checking file paths or environment variables
func testInClusterConnectivity() ClusterInfo {
	info := ClusterInfo{
		Found:      false,
		Kubeconfig: "in-cluster",
	}

	// Test kubectl connectivity without kubeconfig (uses in-cluster auth)
	cmd := exec.Command("kubectl", "get", "nodes")
	output, err := cmd.CombinedOutput()

	if err != nil {
		info.Message = fmt.Sprintf("kubectl in-cluster connectivity test failed: %v\nOutput: %s", err, string(output))
		return info
	}

	// If we get here, kubectl worked with in-cluster auth
	info.Found = true
	info.Message = "Cluster is accessible via in-cluster authentication"
	return info
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

// VMExecParams represents the parameters for VM command execution
type VMExecParams struct {
	Namespace string `json:"namespace"`
	VMName    string `json:"vm_name"`
	Command   string `json:"command"`
	Timeout   int    `json:"timeout,omitempty"`
	Verbose   bool   `json:"verbose,omitempty"`
}

// executeVMCommand executes a command on a KubeVirt VM using the vm-exec tool
func executeVMCommand(params VMExecParams) (string, error) {
	// Find vm-exec binary path
	vmExecPath, err := findVMExecBinary()
	if err != nil {
		return "", fmt.Errorf("vm-exec binary not found: %v", err)
	}

	// Build command arguments
	args := []string{
		"-n", params.Namespace,
		"-v", params.VMName,
		"-c", params.Command,
	}

	// Add kubeconfig only if we have one available
	kubeconfigPath := findKubeconfigPath()
	// If no kubeconfig, kubectl will automatically try in-cluster authentication
	if kubeconfigPath != "" {
		args = append([]string{"--kubeconfig", kubeconfigPath}, args...)
	}

	// Add optional parameters
	if params.Timeout > 0 {
		args = append(args, "-t", fmt.Sprintf("%d", params.Timeout))
	}
	if params.Verbose {
		args = append(args, "--verbose")
	}

	// Execute vm-exec command
	cmd := exec.Command(vmExecPath, args...)
	output, err := cmd.CombinedOutput()

	if err != nil {
		return "", fmt.Errorf("vm-exec failed: %v\nOutput: %s", err, string(output))
	}

	return string(output), nil
}

// findKubeconfigPath finds the kubeconfig file path using the same logic as detectKubevirtciCluster
func findKubeconfigPath() string {
	// First, check if KUBECONFIG environment variable is set
	existingKubeconfig := os.Getenv("KUBECONFIG")
	if existingKubeconfig != "" {
		if _, err := os.Stat(existingKubeconfig); err == nil {
			return existingKubeconfig
		}
	}

	// Second, check GLOBAL_KUBECONFIG
	globalKubeconfig := os.Getenv("GLOBAL_KUBECONFIG")
	if globalKubeconfig != "" {
		if _, err := os.Stat(globalKubeconfig); err == nil {
			return globalKubeconfig
		}
	}

	// Third, check ~/.kube/config
	homeDir, err := os.UserHomeDir()
	if err == nil {
		defaultKubeconfig := homeDir + "/.kube/config"
		if _, err := os.Stat(defaultKubeconfig); err == nil {
			return defaultKubeconfig
		}
	}

	return ""
}

// findVMExecBinary locates the vm-exec binary
func findVMExecBinary() (string, error) {
	// Get the current executable directory
	execPath, err := os.Executable()
	if err != nil {
		return "", err
	}
	execDir := filepath.Dir(execPath)

	// Primary location: bin/ directory in project root
	// Since the MCP binary is now in bin/, vm-exec should be in the same directory
	binPath := filepath.Join(execDir, "vm-exec")
	if _, err := os.Stat(binPath); err == nil {
		return binPath, nil
	}

	// Provide helpful error message with build instructions
	return "", fmt.Errorf("vm-exec binary not found in bin/vm-exec. Please run 'make build-vm-exec' or 'make build' to build required binaries")
}
