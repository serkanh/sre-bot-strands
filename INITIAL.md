## FEATURE

i want to use aws eks mcp servers to get the information about the eks clusters. To test and develop locally lets bring up k3s with docker-compose as well so we can test the functionality locally.

## EXAMPLES

AWS EKS MCP Servers.

```
{
  "mcpServers": {
    "awslabs.eks-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.eks-mcp-server@latest",
        "--allow-write",
        "--allow-sensitive-data-access"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "autoApprove": [],
      "disabled": false
    }
  }
}
```
### K3s with docker-compose
https://sachua.github.io/post/Lightweight%20Kubernetes%20Using%20Docker%20Compose.html
```
version: '3.7'
services:
  server:
    image: rancher/k3s:v1.24.0-rc1-k3s1-amd64
    networks:
    - default
    command: server
    tmpfs:
    - /run
    - /var/run
    ulimits:
      nproc: 65535
      nofile:
        soft: 65535
        hard: 65535
    privileged: true
    restart: always
    environment:
    # - K3S_TOKEN=${K3S_PASSWORD_1} # Only required if we are running more than 1 node
    - K3S_KUBECONFIG_OUTPUT=/output/kubeconfig.yaml
    - K3S_KUBECONFIG_MODE=666
    volumes:
    - k3s-server:/var/lib/rancher/k3s
    # This is just so that we get the kubeconfig file out
    - ./k3s_data/kubeconfig:/output
    - ./k3s_data/docker_images:/var/lib/rancher/k3s/agent/images
    expose:
    - "6443"  # Kubernetes API Server
    - "80"    # Ingress controller port 80
    - "443"   # Ingress controller port 443
    ports:
    - 6443:6443
volumes:
  k3s-server: {}
networks:
  default:
    ipam:
      driver: default
      config:
        - subnet: "172.98.0.0/16" # Self-defined subnet on local machine
```
- https://raw.githubusercontent.com/its-knowledge-sharing/K3S-Demo/refs/heads/production/docker-compose.yaml
## DOCUMENTATION
- [AWS EKS MCP Servers](https://awslabs.github.io/mcp/servers/eks-mcp-server/)

## OTHER CONSIDERATIONS
