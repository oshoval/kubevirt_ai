#!/usr/bin/env bats

setup() {
    # Create VMs using inline manifests if they don't exist
    if ! kubectl get vm vmi1 >/dev/null 2>&1; then
        echo "Creating vmi1..."
        kubectl apply -f - <<EOF
apiVersion: kubevirt.io/v1
kind: VirtualMachine
metadata:
  name: vmi1
spec:
  runStrategy: Always
  template:
    metadata:
      labels:
        kubevirt.io/domain: vmi1
    spec:
      domain:
        devices:
          disks:
          - disk:
              bus: virtio
            name: containerdisk
          - disk:
              bus: virtio
            name: cloudinitdisk
          interfaces:
          - name: default
            masquerade: {}
        machine:
          type: ""
        resources:
          requests:
            memory: 1024M
      networks:
      - name: default
        pod: {}
      terminationGracePeriodSeconds: 0
      volumes:
      - name: containerdisk
        containerDisk:
          image: quay.io/kubevirt/fedora-with-test-tooling-container-disk:v1.6.0
      - name: cloudinitdisk
        cloudInitNoCloud:
          networkData: |
            version: 2
            ethernets:
              eth0:
                dhcp4: true
EOF
    fi

    if ! kubectl get vm vmi2 >/dev/null 2>&1; then
        echo "Creating vmi2..."
        kubectl apply -f - <<EOF
apiVersion: kubevirt.io/v1
kind: VirtualMachine
metadata:
  name: vmi2
spec:
  runStrategy: Always
  template:
    metadata:
      labels:
        kubevirt.io/domain: vmi2
    spec:
      domain:
        devices:
          disks:
          - disk:
              bus: virtio
            name: containerdisk
          - disk:
              bus: virtio
            name: cloudinitdisk
          interfaces:
          - name: default
            masquerade: {}
        machine:
          type: ""
        resources:
          requests:
            memory: 1024M
      networks:
      - name: default
        pod: {}
      terminationGracePeriodSeconds: 0
      volumes:
      - name: containerdisk
        containerDisk:
          image: quay.io/kubevirt/fedora-with-test-tooling-container-disk:v1.6.0
      - name: cloudinitdisk
        cloudInitNoCloud:
          networkData: |
            version: 2
            ethernets:
              eth0:
                dhcp4: true
EOF
    fi

    # Wait for VMs to be ready (with timeout)
    echo "Waiting for VMs to be ready..."
    timeout=300  # 5 minutes
    start_time=$(date +%s)

    while true; do
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))

        if [ $elapsed -gt $timeout ]; then
            fail "Timeout waiting for VMs to be ready after ${timeout}s"
        fi

        vm1_ready=$(kubectl get vm vmi1 -o jsonpath='{.status.ready}' 2>/dev/null || echo "false")
        vm2_ready=$(kubectl get vm vmi2 -o jsonpath='{.status.ready}' 2>/dev/null || echo "false")

        if [ "$vm1_ready" = "true" ] && [ "$vm2_ready" = "true" ]; then
            break
        fi

        echo "VMs not ready yet (${elapsed}s elapsed), waiting..."
        sleep 5
    done

    # Get VM IP addresses
    VM1_IP=$(kubectl get vmi vmi1 -o jsonpath='{.status.interfaces[0].ipAddress}')
    VM2_IP=$(kubectl get vmi vmi2 -o jsonpath='{.status.interfaces[0].ipAddress}')

    [ -n "$VM1_IP" ] || fail "Cannot get vmi1 IP address"
    [ -n "$VM2_IP" ] || fail "Cannot get vmi2 IP address"

    echo "VMs ready - vmi1: $VM1_IP, vmi2: $VM2_IP"
}

@test "vmis can ping each other" {
    # VM1 -> VM2
    VM2_IP=$(kubectl get vmi vmi2 -o jsonpath='{.status.interfaces[0].ipAddress}')
    run ./bin/vm-exec -n default -v vmi1 -c "ping -c 3 $VM2_IP"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "3 packets transmitted, 3 received, 0% packet loss" ]]

    # VM2 -> VM1
    VM1_IP=$(kubectl get vmi vmi1 -o jsonpath='{.status.interfaces[0].ipAddress}')
    run ./bin/vm-exec -n default -v vmi2 -c "ping -c 3 $VM1_IP"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "3 packets transmitted, 3 received, 0% packet loss" ]]
}

teardown() {
    # Cleanup VMs after tests
    echo "Cleaning up VMs..."
    kubectl delete vm vmi1 vmi2 --ignore-not-found=true --force --grace-period=0
    echo "Test completed. VMs cleaned up."
}
