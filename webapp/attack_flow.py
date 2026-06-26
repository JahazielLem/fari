"""Read-only parsing and layout for Attack Flow Builder JSON files."""

from __future__ import annotations

import json
from collections import defaultdict, deque


NODE_TYPES = {
    "attack-flow",
    "attack-action",
    "attack-condition",
    "attack-operator",
    "attack-asset",
    "attack-grouping",
    "grouping",
}


class AttackFlowError(ValueError):
    pass


def parse_attack_flow(raw: bytes) -> dict:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AttackFlowError("The AFB file must contain valid UTF-8 JSON.") from exc

    objects = payload.get("objects") if isinstance(payload, dict) else None
    if not isinstance(objects, list):
        raise AttackFlowError("The AFB file must contain an objects array.")

    if payload.get("schema") == "attack_flow_v2":
        return _parse_builder_v2(payload, objects)
    return _parse_stix(objects)


def _parse_stix(objects: list[dict]) -> dict:
    """Parse an exported STIX 2.1 Attack Flow bundle."""

    source_nodes = {
        item.get("id"): item
        for item in objects
        if isinstance(item, dict)
        and item.get("type") in NODE_TYPES
        and isinstance(item.get("id"), str)
    }
    flows = [item for item in source_nodes.values() if item.get("type") == "attack-flow"]
    if not flows:
        raise AttackFlowError("No attack-flow object was found in the AFB file.")
    flow = flows[0]

    nodes = []
    for node_id, item in source_nodes.items():
        node_type = item.get("type", "unknown")
        name = item.get("name") or item.get("operator") or node_type.replace("-", " ").title()
        nodes.append(
            {
                "id": node_id,
                "type": node_type,
                "name": str(name),
                "description": str(item.get("description") or ""),
                "context": str(item.get("context") or ""),
                "technique_id": _technique_id(item),
            }
        )

    edge_keys: set[tuple[str, str, str]] = set()
    for item in source_nodes.values():
        for field, label in (
            ("start_refs", "starts"),
            ("effect_refs", "effect"),
            ("on_true_refs", "true"),
            ("on_false_refs", "false"),
            ("object_refs", "groups"),
        ):
            for target in item.get(field, []) or []:
                if item["id"] in source_nodes and target in source_nodes:
                    edge_keys.add((item["id"], target, label))

    for item in objects:
        if not isinstance(item, dict) or item.get("type") != "relationship":
            continue
        source = item.get("source_ref")
        target = item.get("target_ref")
        if source in source_nodes and target in source_nodes:
            edge_keys.add((source, target, str(item.get("relationship_type") or "relates")))

    edges = [{"source": source, "target": target, "label": label} for source, target, label in edge_keys]
    positioned_nodes, width, height = layout_graph(nodes, edges, flow.get("start_refs", []))
    return _add_groups({
        "name": str(flow.get("name") or "Untitled Attack Flow"),
        "description": str(flow.get("description") or ""),
        "nodes": positioned_nodes,
        "edges": edges,
        "width": width,
        "height": height,
        "action_count": sum(node["type"] == "attack-action" for node in nodes),
        "asset_count": sum(node["type"] == "attack-asset" for node in nodes),
        "source_format": "STIX 2.1 Attack Flow",
    })


def _parse_builder_v2(payload: dict, objects: list[dict]) -> dict:
    """Parse the native editable JSON saved by Attack Flow Builder v2."""
    flow = next(
        (item for item in objects if isinstance(item, dict) and item.get("id") == "flow"),
        None,
    )
    if flow is None:
        raise AttackFlowError("No flow object was found in the Attack Flow Builder file.")

    node_ids = {"action", "condition", "operator", "asset", "grouping"}
    source_nodes = [
        item
        for item in objects
        if isinstance(item, dict)
        and item.get("id") in node_ids
        and isinstance(item.get("instance"), str)
    ]
    if not source_nodes:
        raise AttackFlowError("The Attack Flow Builder file contains no reportable flow objects.")

    nodes = []
    for item in source_nodes:
        properties = _properties(item)
        ttp = _pairs(properties.get("ttp"))
        node_type = {
            "action": "attack-action",
            "condition": "attack-condition",
            "operator": "attack-operator",
            "asset": "attack-asset",
            "grouping": "attack-grouping",
        }[item["id"]]
        nodes.append(
            {
                "id": item["instance"],
                "type": node_type,
                "name": str(
                    properties.get("name")
                    or properties.get("operator")
                    or item["id"].replace("-", " ").title()
                ),
                "description": str(properties.get("description") or ""),
                "context": str(properties.get("context") or ""),
                "technique_id": str(
                    ttp.get("subtechnique") or ttp.get("technique") or ""
                ),
            }
        )

    latch_to_anchor: dict[str, str] = {}
    for item in objects:
        if not isinstance(item, dict) or item.get("id") not in {
            "horizontal_anchor",
            "vertical_anchor",
        }:
            continue
        for latch in item.get("latches", []) or []:
            latch_to_anchor[latch] = item.get("instance")

    anchor_to_node: dict[str, str] = {}
    for item in source_nodes:
        for anchor in (item.get("anchors") or {}).values():
            anchor_to_node[anchor] = item["instance"]

    edge_keys: set[tuple[str, str, str]] = set()
    for item in objects:
        if not isinstance(item, dict) or item.get("id") != "dynamic_line":
            continue
        source = anchor_to_node.get(latch_to_anchor.get(item.get("source"), ""))
        target = anchor_to_node.get(latch_to_anchor.get(item.get("target"), ""))
        if source and target and source != target:
            edge_keys.add((source, target, "flow"))
    edges = [
        {"source": source, "target": target, "label": label}
        for source, target, label in edge_keys
    ]

    positioned_nodes, width, height = _builder_layout(nodes, edges, payload.get("layout"))
    flow_properties = _properties(flow)
    return _add_groups({
        "name": str(flow_properties.get("name") or "Untitled Attack Flow"),
        "description": str(flow_properties.get("description") or ""),
        "nodes": positioned_nodes,
        "edges": edges,
        "width": width,
        "height": height,
        "action_count": sum(node["type"] == "attack-action" for node in nodes),
        "asset_count": sum(node["type"] == "attack-asset" for node in nodes),
        "source_format": "Attack Flow Builder v2",
    })


def _add_groups(graph: dict) -> dict:
    """Add a report-oriented grouping view while preserving the original graph."""
    by_id = {node["id"]: node for node in graph["nodes"]}
    group_nodes = [
        node for node in graph["nodes"] if node["type"] in {"attack-grouping", "grouping"}
    ]
    assigned_actions: set[str] = set()
    groups = []
    for group in group_nodes:
        action_ids = set()
        for edge in graph["edges"]:
            if edge["source"] == group["id"]:
                action_ids.add(edge["target"])
            elif edge["target"] == group["id"]:
                action_ids.add(edge["source"])
        actions = sorted(
            [
                by_id[action_id]
                for action_id in action_ids
                if action_id in by_id and by_id[action_id]["type"] == "attack-action"
            ],
            key=lambda item: item["name"].lower(),
        )
        assigned_actions.update(action["id"] for action in actions)
        groups.append(
            {
                "id": group["id"],
                "name": group["name"],
                "description": group["description"],
                "context": group.get("context", ""),
                "actions": actions,
            }
        )
    graph["groups"] = sorted(groups, key=lambda item: item["name"].lower())
    graph["ungrouped_actions"] = sorted(
        [
            node
            for node in graph["nodes"]
            if node["type"] == "attack-action" and node["id"] not in assigned_actions
        ],
        key=lambda item: item["name"].lower(),
    )
    return graph


def _properties(item: dict) -> dict:
    return _pairs(item.get("properties"))


def _pairs(value) -> dict:
    if not isinstance(value, list):
        return {}
    return {
        pair[0]: pair[1]
        for pair in value
        if isinstance(pair, list) and len(pair) == 2 and isinstance(pair[0], str)
    }


def _builder_layout(
    nodes: list[dict], edges: list[dict], source_layout
) -> tuple[list[dict], int, int]:
    if not isinstance(source_layout, dict):
        return layout_graph(nodes, edges, [])
    valid = {
        node["id"]: source_layout[node["id"]]
        for node in nodes
        if isinstance(source_layout.get(node["id"]), list)
        and len(source_layout[node["id"]]) == 2
        and all(isinstance(value, (int, float)) for value in source_layout[node["id"]])
    }
    if len(valid) != len(nodes):
        return layout_graph(nodes, edges, [])
    min_x = min(point[0] for point in valid.values())
    min_y = min(point[1] for point in valid.values())
    positioned = [
        {
            **node,
            "x": int(valid[node["id"]][0] - min_x + 45),
            "y": int(valid[node["id"]][1] - min_y + 45),
        }
        for node in nodes
    ]
    width = max(node["x"] for node in positioned) + 260
    height = max(node["y"] for node in positioned) + 125
    return positioned, width, height


def _technique_id(item: dict) -> str:
    for reference in item.get("external_references", []) or []:
        if not isinstance(reference, dict):
            continue
        external_id = reference.get("external_id")
        if external_id:
            return str(external_id)
    return ""


def layout_graph(nodes: list[dict], edges: list[dict], starts: list[str]) -> tuple[list[dict], int, int]:
    """Produce a deterministic left-to-right layout without modifying the AFB."""
    by_id = {node["id"]: node for node in nodes}
    outgoing: dict[str, list[str]] = defaultdict(list)
    incoming: dict[str, int] = defaultdict(int)
    for edge in edges:
        outgoing[edge["source"]].append(edge["target"])
        incoming[edge["target"]] += 1

    roots = [node_id for node_id in starts if node_id in by_id]
    roots += [
        node["id"]
        for node in nodes
        if incoming[node["id"]] == 0 and node["id"] not in roots
    ]
    levels: dict[str, int] = {}
    queue = deque((node_id, 0) for node_id in roots)
    while queue:
        node_id, level = queue.popleft()
        if node_id in levels and levels[node_id] >= level:
            continue
        levels[node_id] = level
        for target in outgoing[node_id]:
            if level < len(nodes):
                queue.append((target, level + 1))
    for node in nodes:
        levels.setdefault(node["id"], max(levels.values(), default=-1) + 1)

    columns: dict[int, list[dict]] = defaultdict(list)
    for node in nodes:
        columns[levels[node["id"]]].append(node)
    positioned = []
    for level in sorted(columns):
        for row, node in enumerate(sorted(columns[level], key=lambda item: item["name"].lower())):
            positioned.append({**node, "x": 45 + level * 285, "y": 45 + row * 145})
    width = max((node["x"] for node in positioned), default=45) + 260
    height = max((node["y"] for node in positioned), default=45) + 125
    return positioned, width, height
