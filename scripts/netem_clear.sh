#!/usr/bin/env bash
# scripts/netem_clear.sh
# Cleanup script for T1.2 netem latency emulation.
# Removes the netem qdisc from all Kind worker node containers.
#
# USAGE:
#   bash scripts/netem_clear.sh [cluster-name]
#
# Default cluster name: rl-scheduler
# This script ONLY runs docker exec commands (no sudo required on the host).
# The netem module itself (loaded via `sudo modprobe sch_netem`) is not unloaded
# by this script — rebooting the host is the safest way to unload it.
#
# Entry in docs/DECISIONS.md: RULE-001
# Applied by: T1.2

set -euo pipefail

CLUSTER="${1:-rl-scheduler}"

WORKERS=$(docker ps --filter "name=${CLUSTER}-worker" --format "{{.Names}}")

if [ -z "$WORKERS" ]; then
  echo "[netem_clear] No worker containers found for cluster '${CLUSTER}'. Nothing to do."
  exit 0
fi

for WORKER in $WORKERS; do
  echo "[netem_clear] Removing root qdisc on ${WORKER} eth0 ..."
  docker exec "${WORKER}" tc qdisc del dev eth0 root 2>/dev/null \
    && echo "[netem_clear]   Done: ${WORKER}" \
    || echo "[netem_clear]   No qdisc on ${WORKER} (already clean or not applied)"
done

echo "[netem_clear] Finished. All netem qdiscs removed."
