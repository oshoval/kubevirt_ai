# MCP Cluster Detection Bug Report

**Agent Command:** python main.py --query 'check if MCP can detect the cluster using GLOBAL_KUBECONFIG'

## Bug Found: MCP Tool Cannot Detect GLOBAL_KUBECONFIG Environment Variable

### Description
The MCP `detect_kubevirtci_cluster` tool fails to detect the GLOBAL_KUBECONFIG environment variable even when it is properly set in the shell environment.

### Evidence
1. **Environment Variable Exists**: `env | grep -i kube` shows `GLOBAL_KUBECONFIG=/home/oshoval/work/kubeconfig`
2. **File Exists**: The kubeconfig file exists at the specified path and is readable
3. **Manual kubectl Works**: Direct kubectl commands using the GLOBAL_KUBECONFIG path work perfectly
4. **MCP Tool Fails**: Multiple calls to `detect_kubevirtci_cluster` return "GLOBAL_KUBECONFIG environment variable is not set"

### Test Results
- ✅ GLOBAL_KUBECONFIG environment variable is set: `/home/oshoval/work/kubeconfig`
- ✅ Kubeconfig file exists and is readable (4176 bytes)
- ✅ kubectl connectivity test successful with the kubeconfig
- ❌ MCP tool cannot detect the environment variable
- ❌ MCP tool returns false negative despite proper environment setup

### Impact
- Users cannot rely on MCP auto-detection when GLOBAL_KUBECONFIG is set
- Manual kubeconfig specification required as workaround
- Tool behavior is inconsistent with environment variable visibility

### Suggested Fix
- Investigate why MCP tool environment isolation prevents access to GLOBAL_KUBECONFIG
- Ensure MCP tool process inherits parent environment variables
- Add debugging output to show what environment variables the MCP tool can see

### Workaround
Use explicit kubeconfig path in kubectl commands: `kubectl --kubeconfig=$GLOBAL_KUBECONFIG <command>`

### Bug Classification
**Infrastructure Bug** - MCP tool environment variable detection failure
