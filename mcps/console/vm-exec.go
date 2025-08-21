package main

import (
	"context"
	"fmt"
	"io"
	"os"
	"regexp"
	"strings"
	"time"

	expect "github.com/google/goexpect"
	"github.com/spf13/pflag"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/tools/clientcmd"

	v1 "kubevirt.io/api/core/v1"
	kubecli "kubevirt.io/client-go/kubecli"
	kvcorev1 "kubevirt.io/client-go/kubevirt/typed/core/v1"
	"kubevirt.io/client-go/log"
)

var (
	namespace  string
	vmName     string
	command    string
	timeout    int
	kubeconfig string
	verbose    bool
)

const (
	PromptExpression = `(\$ |\# )`
)

func main() {
	pflag.StringVarP(&namespace, "namespace", "n", "default", "Namespace of the VM")
	pflag.StringVarP(&vmName, "vm", "v", "", "Name of the VM (required)")
	pflag.StringVarP(&command, "command", "c", "", "Command to execute in the VM (required)")
	pflag.IntVarP(&timeout, "timeout", "t", 30, "Timeout in seconds")
	pflag.StringVar(&kubeconfig, "kubeconfig", "", "Path to kubeconfig file")
	pflag.BoolVar(&verbose, "verbose", false, "Verbose output")

	pflag.Parse()

	if vmName == "" {
		fmt.Fprintf(os.Stderr, "Error: VM name is required\n")
		pflag.Usage()
		os.Exit(1)
	}

	if command == "" {
		fmt.Fprintf(os.Stderr, "Error: Command is required\n")
		pflag.Usage()
		os.Exit(1)
	}

	log.InitializeLogging("vm-exec")

	// Create Kubernetes client
	var config clientcmd.ClientConfig
	if kubeconfig != "" {
		config = clientcmd.NewNonInteractiveDeferredLoadingClientConfig(
			&clientcmd.ClientConfigLoadingRules{ExplicitPath: kubeconfig},
			&clientcmd.ConfigOverrides{},
		)
	} else {
		config = clientcmd.NewNonInteractiveDeferredLoadingClientConfig(
			clientcmd.NewDefaultClientConfigLoadingRules(),
			&clientcmd.ConfigOverrides{},
		)
	}

	clientConfig, err := config.ClientConfig()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error creating client config: %v\n", err)
		os.Exit(1)
	}

	virtClient, err := kubecli.GetKubevirtClientFromRESTConfig(clientConfig)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error creating KubeVirt client: %v\n", err)
		os.Exit(1)
	}

	vmExec := &VMExec{
		client:    virtClient,
		namespace: namespace,
		vmName:    vmName,
		command:   command,
		timeout:   time.Duration(timeout) * time.Second,
		verbose:   verbose,
	}

	// Execute command on VM
	output, exitCode, err := vmExec.ExecuteCommand()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	// Print output with trailing newline
	if output != "" {
		fmt.Print(output)
		if !strings.HasSuffix(output, "\n") {
			fmt.Println()
		}
	}

	// Exit with the command's exit code
	os.Exit(exitCode)
}

type VMExec struct {
	client    kubecli.KubevirtClient
	namespace string
	vmName    string
	command   string
	timeout   time.Duration
	verbose   bool
}

func (ve *VMExec) ExecuteCommand() (string, int, error) {
	ctx := context.Background()

	// Get VMI
	vmi, err := ve.getRunningVMI(ctx)
	if err != nil {
		return "", 1, err
	}

	if ve.verbose {
		fmt.Printf("Found running VMI: %s\n", vmi.Name)
		vmiType := ve.getVMIType(vmi)
		fmt.Printf("VM Type: %s\n", vmiType)
		fmt.Printf("Executing command: %s\n", ve.command)
	}

	// Connect to console and execute command
	return ve.executeViaConsole(vmi)
}

func (ve *VMExec) getRunningVMI(ctx context.Context) (*v1.VirtualMachineInstance, error) {
	// Try to get VMI first
	vmi, err := ve.client.VirtualMachineInstance(ve.namespace).Get(ctx, ve.vmName, metav1.GetOptions{})
	if err != nil {
		// If VMI not found, try VM
		vm, vmErr := ve.client.VirtualMachine(ve.namespace).Get(ctx, ve.vmName, metav1.GetOptions{})
		if vmErr != nil {
			return nil, fmt.Errorf("neither VMI nor VM found with name '%s' in namespace '%s': %v, %v", ve.vmName, ve.namespace, err, vmErr)
		}

		if vm.Status.PrintableStatus != v1.VirtualMachineStatusRunning {
			return nil, fmt.Errorf("VM '%s' is not running (status: %s)", ve.vmName, vm.Status.PrintableStatus)
		}

		// Get the VMI from running VM
		vmi, err = ve.client.VirtualMachineInstance(ve.namespace).Get(ctx, ve.vmName, metav1.GetOptions{})
		if err != nil {
			return nil, fmt.Errorf("VM is running but VMI not found: %v", err)
		}
	}

	if vmi.Status.Phase != v1.Running {
		return nil, fmt.Errorf("VMI '%s' is not running (phase: %s)", ve.vmName, vmi.Status.Phase)
	}

	// Check if VMI is paused
	for _, cond := range vmi.Status.Conditions {
		if cond.Type == v1.VirtualMachineInstancePaused && cond.Status == "True" {
			return nil, fmt.Errorf("VMI '%s' is paused", ve.vmName)
		}
	}

	return vmi, nil
}

func (ve *VMExec) executeViaConsole(vmi *v1.VirtualMachineInstance) (string, int, error) {
	vmiType := ve.getVMIType(vmi)
	if vmiType == "" {
		return "", 1, fmt.Errorf("unknown VM type - cannot determine login method")
	}

	if ve.verbose {
		fmt.Printf("Connecting to VM console...\n")
	}

	// Connect to console
	expecter, err := ve.newExpecter(vmi)
	if err != nil {
		return "", 1, fmt.Errorf("failed to connect to console: %v", err)
	}
	defer expecter.Close()

	// Login based on VM type
	if err := ve.loginToVM(expecter, vmi, vmiType); err != nil {
		return "", 1, fmt.Errorf("failed to login to VM: %v", err)
	}

	if ve.verbose {
		fmt.Printf("Successfully logged in to VM\n")
	}

	// Execute command and get result
	return ve.runCommandOnConsole(expecter, ve.command)
}

func (ve *VMExec) newExpecter(vmi *v1.VirtualMachineInstance) (expect.Expecter, error) {
	const connectionTimeout = 10 * time.Second

	// Create console connection exactly like the tests do
	vmiReader, vmiWriter := io.Pipe()
	expecterReader, expecterWriter := io.Pipe()

	serialConsoleOptions := &kvcorev1.SerialConsoleOptions{ConnectionTimeout: connectionTimeout}
	con, err := ve.client.VirtualMachineInstance(vmi.Namespace).SerialConsole(vmi.Name, serialConsoleOptions)
	if err != nil {
		return nil, err
	}

	resCh := make(chan error)
	go func() {
		resCh <- con.Stream(kvcorev1.StreamOptions{
			In:  vmiReader,
			Out: expecterWriter,
		})
	}()

	opts := []expect.Option{expect.SendTimeout(connectionTimeout), expect.Verbose(ve.verbose)}
	expecter, _, err := expect.SpawnGeneric(&expect.GenOptions{
		In:  vmiWriter,
		Out: expecterReader,
		Wait: func() error {
			return <-resCh
		},
		Close: func() error {
			expecterWriter.Close()
			vmiReader.Close()
			return nil
		},
		Check: func() bool { return true },
	}, connectionTimeout, opts...)

	return expecter, err
}

func (ve *VMExec) loginToVM(expecter expect.Expecter, vmi *v1.VirtualMachineInstance, vmiType string) error {
	const promptTimeout = 5 * time.Second
	const loginTimeout = 60 * time.Second

	// Send newline to see current state
	if err := expecter.Send("\n"); err != nil {
		return err
	}

	switch vmiType {
	case "fedora":
		return ve.loginToFedora(expecter, vmi, loginTimeout, promptTimeout)
	case "cirros":
		return ve.loginToCirros(expecter, vmi, loginTimeout, promptTimeout)
	case "alpine":
		return ve.loginToAlpine(expecter, vmi, loginTimeout, promptTimeout)
	default:
		return fmt.Errorf("unsupported VM type: %s", vmiType)
	}
}

func (ve *VMExec) loginToFedora(expecter expect.Expecter, vmi *v1.VirtualMachineInstance, loginTimeout, promptTimeout time.Duration) error {
	hostName := ve.sanitizeHostname(vmi)

	// Check if already logged in
	loggedInPromptRegex := fmt.Sprintf(
		`(\[fedora@(localhost|fedora|%s|%s) ~\]\$ |\[root@(localhost|fedora|%s|%s) fedora\]\# )`,
		vmi.Name, hostName, vmi.Name, hostName,
	)

	b := []expect.Batcher{
		&expect.BSnd{S: "\n"},
		&expect.BExp{R: loggedInPromptRegex},
	}
	_, err := expecter.ExpectBatch(b, promptTimeout)
	if err == nil {
		return nil // Already logged in
	}

	// Login sequence
	b = []expect.Batcher{
		&expect.BSnd{S: "\n"},
		&expect.BSnd{S: "\n"},
		&expect.BExp{R: fmt.Sprintf(`(localhost|fedora|%s|%s) login: `, vmi.Name, hostName)},
		&expect.BSnd{S: "fedora\n"},
		&expect.BExp{R: "Password:"},
		&expect.BSnd{S: "fedora\n"},
		&expect.BExp{R: loggedInPromptRegex},
		&expect.BSnd{S: "sudo su\n"},
		&expect.BExp{R: PromptExpression},
	}

	_, err = expecter.ExpectBatch(b, loginTimeout)
	return err
}

func (ve *VMExec) loginToCirros(expecter expect.Expecter, vmi *v1.VirtualMachineInstance, loginTimeout, promptTimeout time.Duration) error {
	hostName := ve.sanitizeHostname(vmi)

	// Check if already logged in
	_, _, err := expecter.Expect(regexp.MustCompile(`\$`), promptTimeout)
	if err == nil {
		return nil // Already logged in
	}

	// Login sequence
	b := []expect.Batcher{
		&expect.BSnd{S: "\n"},
		&expect.BExp{R: "login as 'cirros' user. default password: 'gocubsgo'. use 'sudo' for root."},
		&expect.BSnd{S: "\n"},
		&expect.BExp{R: hostName + " login:"},
		&expect.BSnd{S: "cirros\n"},
		&expect.BExp{R: "Password:"},
		&expect.BSnd{S: "gocubsgo\n"},
		&expect.BExp{R: PromptExpression},
	}

	_, err = expecter.ExpectBatch(b, loginTimeout)
	return err
}

func (ve *VMExec) loginToAlpine(expecter expect.Expecter, vmi *v1.VirtualMachineInstance, loginTimeout, promptTimeout time.Duration) error {
	hostName := ve.sanitizeHostname(vmi)

	// Check if already logged in
	b := []expect.Batcher{
		&expect.BSnd{S: "\n"},
		&expect.BExp{R: fmt.Sprintf(`(localhost|%s):~\# `, hostName)},
	}
	_, err := expecter.ExpectBatch(b, promptTimeout)
	if err == nil {
		return nil // Already logged in
	}

	// Login sequence
	b = []expect.Batcher{
		&expect.BSnd{S: "\n"},
		&expect.BExp{R: fmt.Sprintf(`(localhost|%s) login: `, hostName)},
		&expect.BSnd{S: "root\n"},
		&expect.BExp{R: PromptExpression},
	}

	_, err = expecter.ExpectBatch(b, loginTimeout)
	return err
}

func (ve *VMExec) runCommandOnConsole(expecter expect.Expecter, command string) (string, int, error) {
	// Send command
	if err := expecter.Send(command + "\n"); err != nil {
		return "", 1, fmt.Errorf("failed to send command: %v", err)
	}

	// Wait for command completion and capture output using batch
	b := []expect.Batcher{
		&expect.BExp{R: PromptExpression}, // Wait for prompt after command
		&expect.BSnd{S: "echo $?\n"},      // Send exit code check
		&expect.BExp{R: PromptExpression}, // Wait for prompt after exit code
	}

	res, err := expecter.ExpectBatch(b, ve.timeout)
	if err != nil {
		return "", 1, fmt.Errorf("command execution failed: %v", err)
	}

	// Extract output and exit code
	var output string
	var exitCode int = 0

	if len(res) >= 2 {
		// Parse command output from the second buffer (after echo $?)
		// Buffer format: "whoami\r\nroot\r\n[root@vmi2 fedora]# echo $?\r\n0\r\n[root@vmi2"
		buffer := res[1].Output

		// Extract command output between command and "echo $?"
		commandPrefix := command + "\r\n"
		if idx := strings.Index(buffer, commandPrefix); idx != -1 {
			start := idx + len(commandPrefix)
			remaining := buffer[start:]

			// Find the end of command output (before "echo $?")
			if endIdx := strings.Index(remaining, "\r\n["); endIdx != -1 {
				output = remaining[:endIdx]
			}
		}

		// TODO: Parse exit code from the echo $? command
		// For now, assume success if we got output without connection errors
		exitCode = 0
	}

	return output, exitCode, nil
}

func (ve *VMExec) getVMIType(vmi *v1.VirtualMachineInstance) string {
	// Check container disk images to determine VM type
	for _, volume := range vmi.Spec.Volumes {
		if volume.VolumeSource.ContainerDisk == nil {
			continue
		}

		image := volume.VolumeSource.ContainerDisk.Image
		if strings.Contains(image, "fedora") {
			return "fedora"
		} else if strings.Contains(image, "cirros") {
			return "cirros"
		} else if strings.Contains(image, "alpine") {
			return "alpine"
		}
	}

	// Check labels as fallback
	if vmi.Labels != nil {
		if os, exists := vmi.Labels["kubevirt.io/os"]; exists {
			return os
		}
	}

	return ""
}

func (ve *VMExec) sanitizeHostname(vmi *v1.VirtualMachineInstance) string {
	// Simple hostname sanitization - remove invalid characters
	hostname := vmi.Name
	hostname = strings.ReplaceAll(hostname, "_", "-")
	return hostname
}
