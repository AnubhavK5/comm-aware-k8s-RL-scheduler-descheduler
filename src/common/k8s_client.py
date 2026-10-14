"""Kubernetes API Client wrapper for RL Scheduler and Descheduler."""

import logging
import time
from typing import Dict, List, Optional, Any
from kubernetes import client, config
from src.common.config import KUBECONFIG, SYSTEM_NAMESPACES, MIN_POD_AGE_SECONDS

logger = logging.getLogger(__name__)

class K8sClient:
    def __init__(self, kubeconfig_path: Optional[str] = None):
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes configuration.")
        except config.ConfigException:
            config.load_kube_config(config_file=kubeconfig_path or KUBECONFIG)
            logger.info(f"Loaded kubeconfig from {kubeconfig_path or KUBECONFIG}.")

        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.custom_api = client.CustomObjectsApi()
        self.policy_v1 = client.PolicyV1Api()
        self._eviction_history: Dict[str, float] = {}

    def get_nodes(self) -> List[Dict[str, Any]]:
        """Fetch worker nodes and their allocatable capacity."""
        nodes = self.core_v1.list_node().items
        worker_nodes = []
        for n in nodes:
            # Skip control-plane/master nodes for workloads if tainted
            taints = n.spec.taints or []
            is_control_plane = any(
                t.key in ["node-role.kubernetes.io/control-plane", "node-role.kubernetes.io/master"]
                for t in taints
            )
            allocatable = n.status.allocatable
            cpu_cores = self._parse_cpu(allocatable.get("cpu", "0"))
            mem_bytes = self._parse_memory(allocatable.get("memory", "0"))

            worker_nodes.append({
                "name": n.metadata.name,
                "is_control_plane": is_control_plane,
                "cpu_allocatable_cores": cpu_cores,
                "mem_allocatable_bytes": mem_bytes,
                "labels": n.metadata.labels or {},
                "ip": next((addr.address for addr in n.status.addresses if addr.type == "InternalIP"), ""),
            })
        return worker_nodes

    def get_node_metrics(self) -> Dict[str, Dict[str, float]]:
        """Fetch real-time CPU and Memory usage per node from metrics.k8s.io."""
        metrics_dict = {}
        try:
            res = self.custom_api.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="nodes"
            )
            for item in res.get("items", []):
                node_name = item["metadata"]["name"]
                usage = item.get("usage", {})
                cpu_cores = self._parse_cpu(usage.get("cpu", "0"))
                mem_bytes = self._parse_memory(usage.get("memory", "0"))
                metrics_dict[node_name] = {
                    "cpu_usage_cores": cpu_cores,
                    "mem_usage_bytes": mem_bytes,
                }
        except Exception as e:
            logger.warning(f"Failed to fetch node metrics: {e}")
        return metrics_dict

    def get_pods(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """List running application pods."""
        if namespace:
            pod_list = self.core_v1.list_namespaced_pod(namespace=namespace).items
        else:
            pod_list = self.core_v1.list_pod_for_all_namespaces().items

        running_pods = []
        for p in pod_list:
            if p.metadata.namespace in SYSTEM_NAMESPACES:
                continue
            if p.status.phase != "Running":
                continue

            creation_ts = p.metadata.creation_timestamp.timestamp() if p.metadata.creation_timestamp else time.time()
            age_sec = time.time() - creation_ts

            owner_kind = ""
            owner_name = ""
            if p.metadata.owner_references:
                owner = p.metadata.owner_references[0]
                owner_kind = owner.kind
                owner_name = owner.name

            running_pods.append({
                "name": p.metadata.name,
                "namespace": p.metadata.namespace,
                "node_name": p.spec.node_name,
                "ip": p.status.pod_ip,
                "labels": p.metadata.labels or {},
                "age_seconds": age_sec,
                "owner_kind": owner_kind,
                "owner_name": owner_name,
            })
        return running_pods

    def get_pod_metrics(self, namespace: Optional[str] = None) -> Dict[str, Dict[str, float]]:
        """Fetch actual CPU and Memory consumption per pod from metrics.k8s.io."""
        pod_metrics = {}
        try:
            if namespace:
                res = self.custom_api.list_namespaced_custom_object(
                    group="metrics.k8s.io",
                    version="v1beta1",
                    namespace=namespace,
                    plural="pods"
                )
            else:
                res = self.custom_api.list_cluster_custom_object(
                    group="metrics.k8s.io",
                    version="v1beta1",
                    plural="pods"
                )
            for item in res.get("items", []):
                p_name = item["metadata"]["name"]
                ns = item["metadata"]["namespace"]
                total_cpu = 0.0
                total_mem = 0.0
                for c in item.get("containers", []):
                    total_cpu += self._parse_cpu(c.get("usage", {}).get("cpu", "0"))
                    total_mem += self._parse_memory(c.get("usage", {}).get("memory", "0"))
                pod_metrics[f"{ns}/{p_name}"] = {
                    "cpu_cores": total_cpu,
                    "mem_bytes": total_mem,
                }
        except Exception as e:
            logger.warning(f"Failed to fetch pod metrics: {e}")
        return pod_metrics

    def can_evict_pod(self, pod: Dict[str, Any], cooldown_seconds: int = 120) -> bool:
        """Check if pod passes descheduling safety constraints."""
        ns = pod["namespace"]
        name = pod["name"]
        full_name = f"{ns}/{name}"

        # 1. Namespace guard
        if ns in SYSTEM_NAMESPACES:
            return False

        # 2. Age guard (avoid evicting newly scheduled pods)
        if pod.get("age_seconds", 0) < MIN_POD_AGE_SECONDS:
            return False

        # 3. Workload kind guard: never evict standalone pods, DaemonSets, or Jobs
        owner_kind = pod.get("owner_kind", "")
        if owner_kind in ["DaemonSet", "Job", ""]:
            return False

        # 4. Eviction cooldown guard to prevent flapping
        last_evicted = self._eviction_history.get(full_name, 0)
        if time.time() - last_evicted < cooldown_seconds:
            return False

        # 5. Replica availability guard: Ensure at least one other ready replica exists
        try:
            deployments = self.apps_v1.list_namespaced_deployment(namespace=ns).items
            for d in deployments:
                selector = d.spec.selector.match_labels or {}
                pod_labels = pod.get("labels", {})
                if all(pod_labels.get(k) == v for k, v in selector.items()):
                    ready_replicas = d.status.ready_replicas or 0
                    if ready_replicas < 2:
                        return False
                    return True
        except Exception as e:
            logger.error(f"Error checking replica availability for {full_name}: {e}")
            return False

        return True

    def evict_pod(self, pod_name: str, namespace: str) -> bool:
        """Execute pod eviction using Kubernetes Eviction subresource."""
        full_name = f"{namespace}/{pod_name}"
        eviction_body = client.V1Eviction(
            metadata=client.V1ObjectMeta(name=pod_name, namespace=namespace),
            delete_options=client.V1DeleteOptions(grace_period_seconds=10)
        )
        try:
            self.core_v1.create_namespaced_pod_eviction(
                name=pod_name,
                namespace=namespace,
                body=eviction_body
            )
            self._eviction_history[full_name] = time.time()
            logger.info(f"Successfully evicted pod {full_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to evict pod {full_name}: {e}")
            return False

    @staticmethod
    def _parse_cpu(cpu_str: str) -> float:
        """Converts CPU string ('500m', '250000n', '1') to cores."""
        if not cpu_str or cpu_str == "0":
            return 0.0
        if cpu_str.endswith("n"):
            return float(cpu_str[:-1]) / 1e9
        if cpu_str.endswith("u"):
            return float(cpu_str[:-1]) / 1e6
        if cpu_str.endswith("m"):
            return float(cpu_str[:-1]) / 1e3
        return float(cpu_str)

    @staticmethod
    def _parse_memory(mem_str: str) -> float:
        """Converts Memory string ('256Mi', '1Gi', '1024Ki') to bytes."""
        if not mem_str or mem_str == "0":
            return 0.0
        units = {
            "Ki": 1024,
            "Mi": 1024 ** 2,
            "Gi": 1024 ** 3,
            "Ti": 1024 ** 4,
            "k": 1000,
            "m": 1000 ** 2,
            "g": 1000 ** 3,
        }
        for u, factor in units.items():
            if mem_str.endswith(u):
                return float(mem_str[:-len(u)]) * factor
        return float(mem_str)
