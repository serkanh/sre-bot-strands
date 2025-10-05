"""Kubernetes Agent with custom K8s tools for K3s and EKS support."""

import logging
from typing import Any

from kubernetes import client, config
from kubernetes.client.rest import ApiException
from strands import Agent, tool
from strands.models import BedrockModel

from app.config import Settings

logger = logging.getLogger(__name__)

# System prompt for Kubernetes specialist
KUBERNETES_SYSTEM_PROMPT = """
You are a Kubernetes specialist with expertise in cluster management and troubleshooting.

Your capabilities include:
- Querying cluster resources (pods, deployments, services, namespaces)
- Analyzing pod logs and events
- Troubleshooting application issues
- Understanding Kubernetes resource states
- Providing actionable recommendations

When analyzing clusters:
1. Use available Kubernetes tools to query actual cluster data
2. Provide clear, specific insights with resource names
3. Explain issues in plain language
4. Suggest concrete troubleshooting steps
5. Format responses with clear sections

You work with both local K3s clusters and production EKS clusters.
Always specify which cluster you're querying.
"""


def _load_kubeconfig(cluster: str) -> None:
    """Load kubeconfig for the specified cluster.

    Args:
        cluster: Cluster identifier (e.g., 'k3s-local' or 'prod-eks')
    """
    settings = Settings()

    if settings.KUBECONFIG:
        # Load from specified kubeconfig file (K3s or custom)
        config.load_kube_config(config_file=settings.KUBECONFIG)
        logger.info("Loaded kubeconfig from %s for cluster %s", settings.KUBECONFIG, cluster)
    else:
        # Try to load from default location (EKS via aws eks update-kubeconfig)
        try:
            config.load_kube_config()
            logger.info("Loaded kubeconfig from default location for cluster %s", cluster)
        except Exception as e:
            logger.warning("Failed to load kubeconfig: %s", e)
            # Try in-cluster config (if running inside K8s)
            config.load_incluster_config()
            logger.info("Loaded in-cluster config for cluster %s", cluster)


def _get_k8s_clients(cluster: str) -> tuple[Any, Any, Any]:
    """Get Kubernetes API clients.

    Args:
        cluster: Cluster identifier

    Returns:
        Tuple of (CoreV1Api, AppsV1Api, BatchV1Api)
    """
    _load_kubeconfig(cluster)

    return (
        client.CoreV1Api(),
        client.AppsV1Api(),
        client.BatchV1Api(),
    )


@tool
def list_namespaces_tool(cluster: str = "default") -> list[str]:
    """List all namespaces in the Kubernetes cluster.

    Args:
        cluster: Cluster identifier (default: 'default')

    Returns:
        List of namespace names
    """
    try:
        api_v1, _, _ = _get_k8s_clients(cluster)
        namespaces = api_v1.list_namespace()
        return [ns.metadata.name for ns in namespaces.items]
    except ApiException as e:
        logger.error("Failed to list namespaces in %s: %s", cluster, e)
        return [f"Error: Failed to list namespaces: {e.reason}"]
    except Exception as e:
        logger.error("Unexpected error listing namespaces in %s: %s", cluster, e)
        return [f"Error: {e!s}"]


@tool
def list_pods_tool(
    cluster: str = "default",
    namespace: str = "default",
    label_selector: str | None = None,
) -> list[dict[str, Any]]:
    """List pods in a namespace.

    Args:
        cluster: Cluster identifier
        namespace: Namespace to list pods from
        label_selector: Optional label selector (e.g., 'app=nginx')

    Returns:
        List of pod information dictionaries
    """
    try:
        api_v1, _, _ = _get_k8s_clients(cluster)

        kwargs = {"namespace": namespace}
        if label_selector:
            kwargs["label_selector"] = label_selector

        pods = api_v1.list_namespaced_pod(**kwargs)

        return [
            {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "status": pod.status.phase,
                "node": pod.spec.node_name,
                "start_time": str(pod.status.start_time) if pod.status.start_time else None,
                "ip": pod.status.pod_ip,
                "labels": pod.metadata.labels or {},
            }
            for pod in pods.items
        ]
    except ApiException as e:
        logger.error("Failed to list pods in %s/%s: %s", cluster, namespace, e)
        return [{"error": f"Failed to list pods: {e.reason}"}]
    except Exception as e:
        logger.error("Unexpected error listing pods in %s/%s: %s", cluster, namespace, e)
        return [{"error": str(e)}]


@tool
def get_pod_details_tool(
    cluster: str = "default",
    pod_name: str = "",
    namespace: str = "default",
) -> dict[str, Any]:
    """Get detailed information about a specific pod.

    Args:
        cluster: Cluster identifier
        pod_name: Name of the pod
        namespace: Namespace of the pod

    Returns:
        Dictionary with detailed pod information
    """
    if not pod_name:
        return {"error": "pod_name is required"}

    try:
        api_v1, _, _ = _get_k8s_clients(cluster)
        pod = api_v1.read_namespaced_pod(pod_name, namespace)

        # Get container statuses
        container_statuses = []
        if pod.status.container_statuses:
            container_statuses = [
                {
                    "name": cs.name,
                    "ready": cs.ready,
                    "restart_count": cs.restart_count,
                    "state": str(cs.state),
                }
                for cs in pod.status.container_statuses
            ]

        return {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": pod.status.phase,
            "node": pod.spec.node_name,
            "start_time": str(pod.status.start_time) if pod.status.start_time else None,
            "ip": pod.status.pod_ip,
            "labels": pod.metadata.labels or {},
            "annotations": pod.metadata.annotations or {},
            "containers": [c.name for c in pod.spec.containers],
            "container_statuses": container_statuses,
            "conditions": [
                {
                    "type": condition.type,
                    "status": condition.status,
                    "last_transition_time": str(condition.last_transition_time),
                }
                for condition in (pod.status.conditions or [])
            ],
        }
    except ApiException as e:
        logger.error("Failed to get pod %s in %s/%s: %s", pod_name, cluster, namespace, e)
        return {"error": f"Failed to get pod details: {e.reason}"}
    except Exception as e:
        logger.error(
            "Unexpected error getting pod %s in %s/%s: %s", pod_name, cluster, namespace, e
        )
        return {"error": str(e)}


@tool
def get_pod_logs_tool(
    cluster: str = "default",
    pod_name: str = "",
    namespace: str = "default",
    container: str | None = None,
    tail_lines: int = 100,
) -> dict[str, Any]:
    """Get logs from a specific pod.

    Args:
        cluster: Cluster identifier
        pod_name: Name of the pod
        namespace: Namespace of the pod
        container: Container name (optional, required for multi-container pods)
        tail_lines: Number of lines to return from the end

    Returns:
        Dictionary with pod logs
    """
    if not pod_name:
        return {"error": "pod_name is required"}

    try:
        api_v1, _, _ = _get_k8s_clients(cluster)

        kwargs = {
            "name": pod_name,
            "namespace": namespace,
            "tail_lines": tail_lines,
        }

        if container:
            kwargs["container"] = container

        logs = api_v1.read_namespaced_pod_log(**kwargs)

        return {
            "pod_name": pod_name,
            "namespace": namespace,
            "cluster": cluster,
            "container": container,
            "logs": logs,
            "log_length": len(logs),
        }
    except ApiException as e:
        logger.error("Failed to get logs for pod %s in %s/%s: %s", pod_name, cluster, namespace, e)
        return {"error": f"Failed to get pod logs: {e.reason}"}
    except Exception as e:
        logger.error(
            "Unexpected error getting logs for pod %s in %s/%s: %s", pod_name, cluster, namespace, e
        )
        return {"error": str(e)}


@tool
def list_deployments_tool(
    cluster: str = "default",
    namespace: str = "default",
) -> list[dict[str, Any]]:
    """List deployments in a namespace.

    Args:
        cluster: Cluster identifier
        namespace: Namespace to list deployments from

    Returns:
        List of deployment information dictionaries
    """
    try:
        _, apps_v1, _ = _get_k8s_clients(cluster)

        deployments = apps_v1.list_namespaced_deployment(namespace=namespace)

        return [
            {
                "name": deploy.metadata.name,
                "namespace": deploy.metadata.namespace,
                "replicas": deploy.spec.replicas,
                "available_replicas": deploy.status.available_replicas or 0,
                "ready_replicas": deploy.status.ready_replicas or 0,
                "strategy": deploy.spec.strategy.type if deploy.spec.strategy else "Unknown",
                "labels": deploy.metadata.labels or {},
            }
            for deploy in deployments.items
        ]
    except ApiException as e:
        logger.error("Failed to list deployments in %s/%s: %s", cluster, namespace, e)
        return [{"error": f"Failed to list deployments: {e.reason}"}]
    except Exception as e:
        logger.error("Unexpected error listing deployments in %s/%s: %s", cluster, namespace, e)
        return [{"error": str(e)}]


@tool
def get_events_tool(
    cluster: str = "default",
    namespace: str = "default",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Get Kubernetes events for a namespace.

    Args:
        cluster: Cluster identifier
        namespace: Namespace to get events from
        limit: Maximum number of events to return

    Returns:
        List of event information dictionaries
    """
    try:
        api_v1, _, _ = _get_k8s_clients(cluster)

        events = api_v1.list_namespaced_event(namespace, limit=limit)

        return [
            {
                "name": event.metadata.name,
                "namespace": event.metadata.namespace,
                "type": event.type,
                "reason": event.reason,
                "message": event.message,
                "first_seen": str(event.first_timestamp) if event.first_timestamp else None,
                "last_seen": str(event.last_timestamp) if event.last_timestamp else None,
                "count": event.count,
                "involved_object": {
                    "kind": event.involved_object.kind,
                    "name": event.involved_object.name,
                }
                if event.involved_object
                else None,
            }
            for event in events.items
        ]
    except ApiException as e:
        logger.error("Failed to get events in %s/%s: %s", cluster, namespace, e)
        return [{"error": f"Failed to get events: {e.reason}"}]
    except Exception as e:
        logger.error("Unexpected error getting events in %s/%s: %s", cluster, namespace, e)
        return [{"error": str(e)}]


@tool
def kubernetes_assistant(query: str) -> str:
    """
    Kubernetes specialist assistant for cluster management and troubleshooting.

    This tool provides expert Kubernetes assistance for:
    - Querying cluster resources (pods, deployments, services, namespaces)
    - Analyzing pod logs and events
    - Troubleshooting application issues
    - Understanding resource states
    - Providing recommendations

    Works with both K3s (local) and EKS (production) clusters.

    Use this tool for queries about:
    - "What pods are running in my cluster?"
    - "Show me logs from pod [name]"
    - "List all deployments in namespace [name]"
    - "What events occurred in the cluster?"
    - "Check the status of pod [name]"
    - "List all namespaces"

    Args:
        query: A Kubernetes-related question or request

    Returns:
        Detailed analysis and response about the cluster
    """
    logger.info("Kubernetes assistant invoked with query: %s", query[:100])

    try:
        settings = Settings()

        # Create Bedrock model
        model = BedrockModel(
            model_id=settings.BEDROCK_MODEL_ID,
            region_name=settings.AWS_REGION,
        )

        # Create Kubernetes agent with K8s tools
        k8s_tools = [
            list_namespaces_tool,
            list_pods_tool,
            get_pod_details_tool,
            get_pod_logs_tool,
            list_deployments_tool,
            get_events_tool,
        ]

        k8s_agent = Agent(
            model=model,
            system_prompt=KUBERNETES_SYSTEM_PROMPT,
            tools=k8s_tools,
        )

        # Execute query
        response = k8s_agent(query)

        logger.info("Kubernetes assistant completed successfully")
        return str(response)

    except Exception as e:
        error_msg = f"Error in Kubernetes assistant: {e!s}"
        logger.exception(error_msg)
        return error_msg


# Export the tool
__all__ = ["kubernetes_assistant"]
