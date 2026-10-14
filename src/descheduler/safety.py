"""Safety checks and disruption guards for the Descheduler."""

import logging
import time
from typing import Dict, Any, List

from src.common.config import SYSTEM_NAMESPACES, MIN_POD_AGE_SECONDS, EVICTION_COOLDOWN_SECONDS

logger = logging.getLogger(__name__)

class SafetyChecker:
    def __init__(self, k8s_client):
        self.k8s_client = k8s_client
        self.deployment_cooldowns: Dict[str, float] = {}

    def get_safe_eviction_candidates(self, pods: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter candidate pods strictly adhering to safety and availability policies."""
        now = time.time()
        safe_candidates = []

        for p in pods:
            ns = p.get("namespace", "default")
            name = p.get("name", "")
            owner_name = p.get("owner_name", "")

            # 1. Namespace filter
            if ns in SYSTEM_NAMESPACES:
                continue

            # 2. Minimum age filter
            if p.get("age_seconds", 0) < MIN_POD_AGE_SECONDS:
                continue

            # 3. Workload kind check (must belong to a ReplicaSet/Deployment)
            if p.get("owner_kind") not in ["ReplicaSet", "Deployment"]:
                continue

            # 4. Deployment-level cooldown filter
            if owner_name and (now - self.deployment_cooldowns.get(owner_name, 0) < EVICTION_COOLDOWN_SECONDS):
                continue

            # 5. Pod replica availability check (k8s client verification)
            if not self.k8s_client.can_evict_pod(p, cooldown_seconds=EVICTION_COOLDOWN_SECONDS):
                continue

            safe_candidates.append(p)

        logger.debug(f"Found {len(safe_candidates)} safe eviction candidates out of {len(pods)} running pods.")
        return safe_candidates

    def mark_evicted(self, pod: Dict[str, Any]):
        """Record eviction timestamp for deployment to enforce cooldown."""
        owner = pod.get("owner_name")
        if owner:
            self.deployment_cooldowns[owner] = time.time()
