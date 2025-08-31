package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

type ClusterInfo struct {
	Found       bool
	Kubeconfig  string
	ClusterType string
	DocsPath    string
	Message     string
}

type Config struct {
	Docs struct {
		Kubernetes string `json:"kubernetes"`
		OpenShift  string `json:"openshift"`
	} `json:"docs"`
}

func loadConfig() (*Config, error) {
	configPath := filepath.Join("config", "config.json")
	data, err := os.ReadFile(configPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %v", err)
	}

	var config Config
	if err := json.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("failed to parse config file: %v", err)
	}

	return &config, nil
}

func detectClusterType(kubeconfigPath string) (string, string, error) {
	// Load configuration
	config, err := loadConfig()
	if err != nil {
		return "", "", fmt.Errorf("failed to load config: %v", err)
	}

	// Detect if cluster is OpenShift or Kubernetes
	var cmd *exec.Cmd
	if kubeconfigPath != "" {
		cmd = exec.Command("kubectl", "--kubeconfig", kubeconfigPath, "api-resources")
	} else {
		// Use in-cluster or default kubeconfig
		cmd = exec.Command("kubectl", "api-resources")
	}

	output, err := cmd.Output()
	if err != nil {
		return "", "", fmt.Errorf("failed to detect cluster type: %v", err)
	}

	// Check for OpenShift-specific resources
	if strings.Contains(string(output), "routes") && strings.Contains(string(output), "openshift.io") {
		return "openshift", config.Docs.OpenShift, nil
	}

	return "kubernetes", config.Docs.Kubernetes, nil
}

func detectKubevirtciCluster() (string, error) {
	// Try sources in priority order until we find a working cluster

	// First, try KUBECONFIG environment variable
	existingKubeconfig := os.Getenv("KUBECONFIG")
	if existingKubeconfig != "" {
		if _, err := os.Stat(existingKubeconfig); err == nil {
			clusterInfo := testClusterConnectivity(existingKubeconfig)
			if clusterInfo.Found {
				clusterType, docsPath, err := detectClusterType(existingKubeconfig)
				if err != nil {
					return "", fmt.Errorf("cluster detection failed: %v", err)
				}
				result := fmt.Sprintf(`Cluster Available via KUBECONFIG environment variable

Setup Commands:
   export KUBECONFIG=%s
   export CLUSTER_TYPE=%s
   export DOCS_FOLDER=%s

Verification:
   kubectl get nodes
   kubectl get kubevirt -n kubevirt

Ready to use %s cluster!`, existingKubeconfig, clusterType, docsPath, clusterType)
				return result, nil
			}
		}
	}

	// Second, try in-cluster authentication (running in a pod)
	clusterInfo := testInClusterConnectivity()
	if clusterInfo.Found {
		clusterType, docsPath, err := detectClusterType("")
		if err != nil {
			return "", fmt.Errorf("cluster detection failed: %v", err)
		}
		result := fmt.Sprintf(`Cluster Available via in-cluster authentication

Environment: Running inside Kubernetes pod
   Service account authentication active
   No kubeconfig configuration needed
   export CLUSTER_TYPE=%s
   export DOCS_FOLDER=%s

Verification:
   kubectl get nodes
   kubectl get kubevirt -n kubevirt

Ready to use %s cluster!`, clusterType, docsPath, clusterType)
		return result, nil
	}

	// Third, try ~/.kube/config
	homeDir, err := os.UserHomeDir()
	if err == nil {
		defaultKubeconfig := homeDir + "/.kube/config"
		if _, err := os.Stat(defaultKubeconfig); err == nil {
			clusterInfo := testClusterConnectivity(defaultKubeconfig)
			if clusterInfo.Found {
				clusterType, docsPath, err := detectClusterType(defaultKubeconfig)
				if err != nil {
					return "", fmt.Errorf("cluster detection failed: %v", err)
				}
				result := fmt.Sprintf(`Cluster Available via ~/.kube/config

Setup Commands:
   export KUBECONFIG=%s
   export CLUSTER_TYPE=%s
   export DOCS_FOLDER=%s

Verification:
   kubectl get nodes
   kubectl get kubevirt -n kubevirt

Ready to use %s cluster!`, defaultKubeconfig, clusterType, docsPath, clusterType)
				return result, nil
			}
		}
	}

	// Fourth, try GLOBAL_KUBECONFIG environment variable
	globalKubeconfig := os.Getenv("GLOBAL_KUBECONFIG")
	if globalKubeconfig != "" {
		if _, err := os.Stat(globalKubeconfig); err == nil {
			clusterInfo := testClusterConnectivity(globalKubeconfig)
			if clusterInfo.Found {
				clusterType, docsPath, err := detectClusterType(globalKubeconfig)
				if err != nil {
					return "", fmt.Errorf("cluster detection failed: %v", err)
				}
				result := fmt.Sprintf(`Cluster Available via GLOBAL_KUBECONFIG

Setup Commands:
   export KUBECONFIG=%s
   export CLUSTER_TYPE=%s
   export DOCS_FOLDER=%s

Verification:
   kubectl get nodes
   kubectl get kubevirt -n kubevirt

Ready to use %s cluster!`, globalKubeconfig, clusterType, docsPath, clusterType)
				return result, nil
			}
		}
	}

	// No working cluster found
	return "No accessible cluster found using any configured kubeconfig source", nil
}

// testInClusterConnectivity tests cluster connectivity using in-cluster authentication
// This approach is simpler and more reliable than checking file paths or environment variables
func testInClusterConnectivity() ClusterInfo {
	info := ClusterInfo{
		Found:      false,
		Kubeconfig: "in-cluster",
	}

	// Test kubectl connectivity without kubeconfig (uses in-cluster auth) with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, "kubectl", "cluster-info")
	output, err := cmd.CombinedOutput()

	if err != nil {
		if ctx.Err() == context.DeadlineExceeded {
			info.Message = "kubectl in-cluster connectivity test timed out after 5 seconds"
		} else {
			info.Message = fmt.Sprintf("kubectl in-cluster connectivity test failed: %v\nOutput: %s", err, string(output))
		}
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

	// Test kubectl connectivity with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, "kubectl", "cluster-info", "--kubeconfig", kubeconfigPath)
	output, err := cmd.CombinedOutput()

	if err != nil {
		if ctx.Err() == context.DeadlineExceeded {
			info.Message = "kubectl connectivity test timed out after 5 seconds"
		} else {
			info.Message = fmt.Sprintf("kubectl connectivity test failed: %v\nOutput: %s", err, string(output))
		}
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
