"""Configuration constants and defaults for RL Scheduler and Descheduler."""

import os

# Cluster & Namespace configuration
KUBECONFIG = os.getenv("KUBECONFIG", os.path.expanduser("~/.kube/config"))
DEFAULT_NAMESPACE = os.getenv("TARGET_NAMESPACE", "default")
SYSTEM_NAMESPACES = {"kube-system", "local-path-storage", "monitoring"}

# Scheduler Extender Configuration
EXTENDER_HOST = os.getenv("EXTENDER_HOST", "0.0.0.0")
EXTENDER_PORT = int(os.getenv("EXTENDER_PORT", "8888"))

# Descheduler Loop Configuration
DESCHEDULER_INTERVAL_SECONDS = int(os.getenv("DESCHEDULER_INTERVAL", "30"))
MIN_POD_AGE_SECONDS = int(os.getenv("MIN_POD_AGE", "60"))
EVICTION_COOLDOWN_SECONDS = int(os.getenv("EVICTION_COOLDOWN", "120"))
MAX_EVICTIONS_PER_CYCLE = int(os.getenv("MAX_EVICTIONS_PER_CYCLE", "1"))

# Telemetry Aggregator Configuration
METRICS_SERVER_ENABLED = True
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
OTEL_RECEIVER_URL = os.getenv("OTEL_RECEIVER_URL", "http://localhost:4318")

# RL Model Hyperparameters & Weights
RESOURCE_WEIGHT = float(os.getenv("RESOURCE_WEIGHT", "0.5"))
COMMUNICATION_WEIGHT = float(os.getenv("COMMUNICATION_WEIGHT", "0.5"))
CHURN_PENALTY = float(os.getenv("CHURN_PENALTY", "2.0"))
EVICTION_COST = float(os.getenv("EVICTION_COST", "0.5"))

# Node State Feature Dimension (from Synopsis Eq. 4.1)
# s = [cpu_eff, mem_eff, node_cpu, node_mem, disk_io, net_lat, node_temp]
NODE_FEATURE_DIM = 7
