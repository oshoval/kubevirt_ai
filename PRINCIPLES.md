# KubeVirt AI Agent - Design Principles & Learning

## Core Philosophy: Minimal Code, Maximum AI Intelligence

### 🧠 AI Autonomy Rules
- **Let AI deduce workflows**: Don't program specific sequences like "export KUBECONFIG then kubectl"
- **AI should figure out**: Environment setup, tool combinations, error handling
- **Avoid hardcoded logic**: No specific command sequences or workflow programming
- **Trust AI reasoning**: The agent should understand tool outputs and chain them logically

### 🛠️ Code Boundaries
- **Only MCPs contain deterministic logic**: All domain-specific logic goes in MCP tools
- **Main agent stays generic**: No KubeVirt-specific or kubectl-specific code
- **Never update MCPs without asking**: MCPs are stable interfaces
- **No hacks or shortcuts**: No programmatic workarounds for what AI should deduce

### 🎯 Task Completion Issues
- **Problem**: Agent stops before completing full missions
- **Root Cause**: Response truncation, not token limits
- **Solution Needed**: Fix conversation flow to ensure full task completion
- **Not Allowed**: Loops, explicit step programming, or workflow orchestration code

### 🔧 Technical Guidelines
- **Environment Variables**: Use for configuration (models, auth) not workflow logic
- **Tool Descriptions**: Should hint at capabilities, not prescribe exact usage
- **Prompt Engineering**: Guide behavior through principles, not step-by-step instructions
- **Model Selection**: Use appropriate models for task complexity

### 📁 File Preservation - CRITICAL RULE
- **NEVER delete files from test log directories**: All generated files are permanent evidence
- **Preserve all test artifacts**: VM configs, manifests, network configs, bug reports
- **Maintain audit trail**: Each file represents test evidence for developers/admins
- **No cleanup of logs**: Files are debugging evidence, not temporary data
- **Examples**: ❌ `rm vm-config.yaml` ✅ Keep all generated files forever

### 📝 Documentation - BREVITY PRINCIPLE
- **Keep documentation short**: 10-20 lines maximum for READMEs
- **No one reads long docs**: If it's longer than one screen, it's too long
- **Essential info only**: Installation, usage, what it does - nothing more
- **Examples**: ❌ 200+ line README ✅ 20 line README with just the basics

### ✅ Recent Improvements
1. **Official Anthropic Pattern**: Implemented true `while True` loop with `response.stop_reason == "tool_use"`
2. **Zero Artificial Limits**: No `max_iterations` in main loop (only safety valve at 50 turns)
3. **Modular Design**: Separated tool extraction, execution, and text extraction into clean helper methods
4. **Natural Completion**: Model decides when mission is complete via `stop_reason`
5. **Perfect Multi-Step Execution**: Agent autonomously executes complex missions (28 tool calls for PASST investigation)
6. **KUBECONFIG Intelligence**: AI correctly extracts and uses KUBECONFIG path across multiple commands
7. **Bug Detection**: Successfully identified documentation/infrastructure issues during PASST testing
8. **Rich Markup Safety**: Added proper escaping for console output containing special characters

### 🎯 Success Metrics
- Agent reads documentation independently
- Agent creates VMs with proper networking
- Agent tests connectivity and reports findings
- Agent completes entire mission in one autonomous session
- Zero hardcoded workflows in main agent code

## Remember: We're building an AI that thinks, not a script that follows steps.
