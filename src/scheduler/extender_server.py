"""Kubernetes Scheduler Extender HTTP Server."""

import logging
from flask import Flask, request, jsonify

from src.common.config import EXTENDER_HOST, EXTENDER_PORT
from src.common.k8s_client import K8sClient
from src.telemetry.aggregator import TelemetryAggregator
from src.telemetry.comm_graph import CommunicationGraph
from src.scheduler.scorer import NodeScorer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SchedulerExtender")

app = Flask(__name__)

# Global instances
k8s_client = K8sClient()
comm_graph = CommunicationGraph()
aggregator = TelemetryAggregator(k8s_client=k8s_client, comm_graph=comm_graph)
scorer = NodeScorer()

@app.route("/healthz", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route("/filter", methods=["POST"])
def filter_nodes():
    """
    Kubernetes Scheduler Extender Filter endpoint.
    Takes ExtenderArgs and returns ExtenderFilterResult.
    """
    args = request.get_json(force=True, silent=True) or {}
    pod = args.get("Pod", {})
    pod_name = pod.get("metadata", {}).get("name", "unknown")
    node_names = args.get("NodeNames")

    if not node_names and "Nodes" in args:
        node_names = [n["metadata"]["name"] for n in args["Nodes"].get("items", [])]

    logger.info(f"Filtering {len(node_names or [])} candidate nodes for pod {pod_name}")

    # Pass all candidate nodes through (relying on kube-scheduler native predicates)
    return jsonify({
        "Nodes": args.get("Nodes"),
        "NodeNames": node_names,
        "FailedNodes": {},
        "Error": ""
    }), 200

@app.route("/prioritize", methods=["POST"])
def prioritize_nodes():
    """
    Kubernetes Scheduler Extender Prioritize endpoint.
    Takes ExtenderArgs and returns HostPriorityList.
    """
    args = request.get_json(force=True, silent=True) or {}
    pod = args.get("Pod", {})
    pod_name = pod.get("metadata", {}).get("name", "unknown")
    node_names = args.get("NodeNames")

    if not node_names and "Nodes" in args:
        node_names = [n["metadata"]["name"] for n in args["Nodes"].get("items", [])]

    if not node_names:
        return jsonify([]), 200

    snapshot = aggregator.get_cluster_snapshot()
    priority_list = scorer.score_candidate_nodes(
        pod_name=pod_name,
        candidate_nodes=node_names,
        snapshot=snapshot
    )

    return jsonify(priority_list), 200

@app.route("/api/v1/telemetry/comm", methods=["POST"])
def ingest_communication_event():
    """
    Ingest inter-pod communication traces.
    Payload: {"src_pod": "str", "dst_pod": "str", "bytes": float, "count": int}
    """
    data = request.get_json(force=True, silent=True) or {}
    src = data.get("src_pod")
    dst = data.get("dst_pod")
    if not src or not dst:
        return jsonify({"error": "src_pod and dst_pod required"}), 400

    bytes_transferred = float(data.get("bytes", 1024.0))
    count = int(data.get("count", 1))

    comm_graph.record_communication(src, dst, bytes_transferred=bytes_transferred, count=count)
    return jsonify({"status": "recorded", "src": src, "dst": dst}), 200

@app.route("/api/v1/cluster-state", methods=["GET"])
def get_cluster_state():
    """API to inspect live cluster state and affinity graph."""
    snapshot = aggregator.get_cluster_snapshot()
    return jsonify({
        "timestamp": snapshot.timestamp,
        "nodes": [
            {
                "name": n["name"],
                "utilization": snapshot.get_node_utilization(n["name"])
            }
            for n in snapshot.nodes if not n.get("is_control_plane", False)
        ],
        "pods": [
            {
                "name": p["name"],
                "node": p.get("node_name"),
                "namespace": p.get("namespace")
            }
            for p in snapshot.pods
        ],
        "active_comm_edges": len(comm_graph.edges)
    }), 200

def main():
    logger.info(f"Starting Scheduler Extender on {EXTENDER_HOST}:{EXTENDER_PORT}")
    app.run(host=EXTENDER_HOST, port=EXTENDER_PORT, debug=False)

if __name__ == "__main__":
    main()
