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
			break
		}

		resp := handleRequest(req)
		encoder.Encode(resp)
	}
}

func handleRequest(req JSONRPCRequest) JSONRPCResponse {
	switch req.Method {
	case "initialize":
		return JSONRPCResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result: map[string]interface{}{
				"protocolVersion": "2024-11-05",
				"serverInfo":      map[string]interface{}{"name": "kubevirt-mcp", "version": "1.0.0"},
				"capabilities":    map[string]interface{}{"tools": map[string]interface{}{}},
			},
		}

	case "tools/list":
		return JSONRPCResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
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
				},
			},
		}

	case "tools/call":
		var params struct {
			Name string `json:"name"`
		}
		json.Unmarshal(req.Params, &params)

		if params.Name == "detect_kubevirtci_cluster" {
			result, err := detectKubevirtciCluster()
			if err != nil {
				return JSONRPCResponse{
					JSONRPC: "2.0",
					ID:      req.ID,
					Error:   &RPCError{Code: -32603, Message: err.Error()},
				}
			}
			return JSONRPCResponse{
				JSONRPC: "2.0",
				ID:      req.ID,
				Result: map[string]interface{}{
					"content": []map[string]interface{}{
						{"type": "text", "text": result},
					},
				},
			}
		}

		return JSONRPCResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Error:   &RPCError{Code: -32601, Message: "Method not found"},
		}

	default:
		return JSONRPCResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Error:   &RPCError{Code: -32601, Message: "Method not found"},
		}
	}
}
