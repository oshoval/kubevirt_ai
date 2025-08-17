module kubevirt-mcp

go 1.23.0

require gopkg.in/yaml.v3 v3.0.1

replace (
	k8s.io/api => k8s.io/api v0.32.5
	k8s.io/apiextensions-apiserver => k8s.io/apiextensions-apiserver v0.32.5
	k8s.io/apimachinery => k8s.io/apimachinery v0.32.5
	k8s.io/apiserver => k8s.io/apiserver v0.32.5
	k8s.io/client-go => k8s.io/client-go v0.32.5
	k8s.io/kube-openapi => k8s.io/kube-openapi v0.0.0-20240430033511-f0e62f92d13f
)
