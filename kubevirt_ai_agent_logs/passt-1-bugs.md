# PASST Network Binding Test - Bug Report #1

## Test Summary
- **Date**: 2025-08-17
- **Test**: PASST network binding functionality in KubeVirt cluster
- **Cluster**: KubeVirtCI k8s-1.33 
- **Documentation Source**: `/home/oshoval/project/user-guide/docs/network/net_binding_plugins/passt.md`

## Test Environment Setup
✅ **PASST binding properly configured in cluster:**
- NetworkBindingPlugins feature gate: ENABLED 
- PASST network binding registration: CONFIGURED in kubevirt CR
- NetworkAttachmentDefinition: EXISTS (default/netbindingpasst)
- Sidecar image: ACCESSIBLE (quay.io/kubevirt/network-passt-binding:20231205_29a16d5c9)

## Critical Infrastructure Issue Found

### BUG #1: Missing PASST CNI Plugin Binary
**Issue**: The `kubevirt-passt-binding` CNI plugin binary is not deployed on cluster nodes.

**Evidence**:
- Documentation requires CNI plugin binary at `/opt/cni/bin/kubevirt-passt-binding`
- Binary is MISSING from both nodes (node01, node02)
- Only `passthru` binary found in `/opt/cni/bin/`, not `kubevirt-passt-binding`

**Impact**: 
- VM creation with PASST binding FAILS immediately
- Pod creation fails at CNI plugin stage
- Complete functionality breakdown

**Root Cause**: CNI plugin deployment step is missing from cluster setup

**Recommended Fix**: 
- Deploy kubevirt-passt-binding CNI binary to `/opt/cni/bin/` on all nodes
- Ensure binary has correct permissions (executable)

### BUG #2: Calico IP Pool Exhaustion 
**Issue**: Calico CNI running out of available IP blocks

**Evidence**:
```
error adding container to network "k8s-pod-network": plugin type="calico" failed (add): 
cannot allocate new block due to per host block limit
```

**Impact**: 
- Cannot create new pods on cluster
- VM creation blocked at network setup phase
- General cluster functionality impaired

**Root Cause**: Calico IP pool configuration limitation

**Recommended Fix**:
- Increase Calico IP pool size or per-host block limit
- Clean up unused IP allocations
- Reconfigure Calico networking parameters

## Test Commands Executed
```bash
# Documentation verification
cat /home/oshoval/project/user-guide/docs/network/net_binding_plugins/passt.md

# Cluster configuration check
kubectl get kubevirt -n kubevirt kubevirt -o yaml
kubectl get network-attachment-definitions netbindingpasst -o yaml

# CNI binary verification
kubectl exec -n cluster-network-addons kube-cni-linux-bridge-plugin-pnktm -- ls -la /opt/cni/bin/

# VM creation attempt
kubectl apply -f passt-1-vm.yaml
kubectl describe vmi vm-net-binding-passt-test
kubectl describe pod virt-launcher-vm-net-binding-passt-test-jhr27
```

## VM Configuration Tested
- Based on documentation example
- Using fedora-with-test-tooling-container-disk:v1.1.0
- PASST binding with HTTP port 80 exposed
- termination-grace-period set to 0 for fast cleanup

## Recommendations
1. **IMMEDIATE**: Deploy kubevirt-passt-binding CNI binary to cluster nodes
2. **HIGH PRIORITY**: Fix Calico IP pool exhaustion issue  
3. **MEDIUM**: Update documentation to include CNI binary deployment automation
4. **LOW**: Consider adding cluster validation scripts to detect missing CNI plugins

## Documentation Gaps
- No automated CNI binary deployment procedure
- Missing troubleshooting section for common CNI issues
- No cluster readiness validation checklist

## Files Created
- `kubevirt_ai_agent_logs/passt-1-vm.yaml` - Test VM configuration
- `kubevirt_ai_agent_logs/passt-1-bugs.md` - This bug report
