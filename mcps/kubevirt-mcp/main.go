package main

import (
	"encoding/json"
	"log"
	"os"
)

// Core MCP structures
type JSONRPCRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      interface{}     `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type JSONRPCResponse struct {
	JSONRPC string      `json:"jsonrpc"`
	ID      interface{} `json:"id"`
	Result  interface{} `json:"result,omitempty"`
	Error   *RPCError   `json:"error,omitempty"`
}

// Helper function to ensure ID is never nil
func safeID(id interface{}) interface{} {
	if id == nil {
		return 0 // Use 0 as default ID for null requests
	}
	return id
}

type RPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

func main() {
	log.SetOutput(os.Stderr)
	log.Println("KubeVirt MCP server running")

	decoder := json.NewDecoder(os.Stdin)
	encoder := json.NewEncoder(os.Stdout)

	for {
		var req JSONRPCRequest
		if err := decoder.Decode(&req); err != nil {
			// Log the error but don't send a response for malformed JSON
			log.Printf("Failed to decode JSON-RPC request: %v", err)
			break
		}

		// Validate that we have a proper request
		if req.JSONRPC != "2.0" {
			log.Printf("Invalid JSON-RPC version: %s", req.JSONRPC)
			continue
		}

		if req.Method == "" {
			log.Printf("Missing method in request")
			// Send error response with proper ID handling
			resp := JSONRPCResponse{
				JSONRPC: "2.0",
				ID:      safeID(req.ID),
				Error:   &RPCError{Code: -32600, Message: "Invalid Request: missing method"},
			}
			encoder.Encode(resp)
			continue
		}

		resp := handleRequest(req)
		if err := encoder.Encode(resp); err != nil {
			log.Printf("Failed to encode response: %v", err)
		}
	}
}

func handleRequest(req JSONRPCRequest) JSONRPCResponse {
	switch req.Method {
	case "initialize":
		return JSONRPCResponse{
			JSONRPC: "2.0",
			ID:      safeID(req.ID),
			Result: map[string]interface{}{
				"protocolVersion": "2024-11-05",
				"serverInfo":      map[string]interface{}{"name": "kubevirt-mcp", "version": "1.0.0"},
				"capabilities":    map[string]interface{}{"tools": map[string]interface{}{}},
			},
		}

	case "tools/list":
		return JSONRPCResponse{
			JSONRPC: "2.0",
			ID:      safeID(req.ID),
			Result: map[string]interface{}{
				"tools": []map[string]interface{}{
					{
						"name":        "detect_kubevirtci_cluster",
						"description": "Detect kubevirtci cluster and set KUBECONFIG",
						"inputSchema": map[string]interface{}{
							"type":       "object",
							"properties": map[string]interface{}{},
						},
					},
					{
						"name":        "vm_exec",
						"description": "Execute a command on a KubeVirt VM via console connection",
						"inputSchema": map[string]interface{}{
							"type": "object",
							"properties": map[string]interface{}{
								"namespace": map[string]interface{}{
									"type":        "string",
									"description": "Kubernetes namespace containing the VM",
									"default":     "default",
								},
								"vm_name": map[string]interface{}{
									"type":        "string",
									"description": "Name of the VM or VMI to execute command on",
								},
								"command": map[string]interface{}{
									"type":        "string",
									"description": "Command to execute inside the VM",
								},
								"timeout": map[string]interface{}{
									"type":        "integer",
									"description": "Timeout in seconds (default: 30)",
									"default":     30,
								},
								"verbose": map[string]interface{}{
									"type":        "boolean",
									"description": "Enable verbose console logging",
									"default":     false,
								},
							},
							"required": []string{"vm_name", "command"},
						},
					},
				},
			},
		}

	case "tools/call":
		var params struct {
			Name      string          `json:"name"`
			Arguments json.RawMessage `json:"arguments,omitempty"`
		}
		json.Unmarshal(req.Params, &params)

		if params.Name == "detect_kubevirtci_cluster" {
			result, err := detectKubevirtciCluster()
			if err != nil {
				return JSONRPCResponse{
					JSONRPC: "2.0",
					ID:      safeID(req.ID),
					Error:   &RPCError{Code: -32603, Message: err.Error()},
				}
			}
			return JSONRPCResponse{
				JSONRPC: "2.0",
				ID:      safeID(req.ID),
				Result: map[string]interface{}{
					"content": []map[string]interface{}{
						{"type": "text", "text": result},
					},
				},
			}
		}

		if params.Name == "vm_exec" {
			var vmParams VMExecParams
			if err := json.Unmarshal(params.Arguments, &vmParams); err != nil {
				return JSONRPCResponse{
					JSONRPC: "2.0",
					ID:      safeID(req.ID),
					Error:   &RPCError{Code: -32602, Message: "Invalid parameters: " + err.Error()},
				}
			}

			// Set defaults if not provided
			if vmParams.Namespace == "" {
				vmParams.Namespace = "default"
			}
			if vmParams.Timeout == 0 {
				vmParams.Timeout = 30
			}

			result, err := executeVMCommand(vmParams)
			if err != nil {
				return JSONRPCResponse{
					JSONRPC: "2.0",
					ID:      safeID(req.ID),
					Error:   &RPCError{Code: -32603, Message: err.Error()},
				}
			}

			return JSONRPCResponse{
				JSONRPC: "2.0",
				ID:      safeID(req.ID),
				Result: map[string]interface{}{
					"content": []map[string]interface{}{
						{"type": "text", "text": result},
					},
				},
			}
		}

		return JSONRPCResponse{
			JSONRPC: "2.0",
			ID:      safeID(req.ID),
			Error:   &RPCError{Code: -32601, Message: "Method not found"},
		}

	default:
		return JSONRPCResponse{
			JSONRPC: "2.0",
			ID:      safeID(req.ID),
			Error:   &RPCError{Code: -32601, Message: "Method not found"},
		}
	}
}
