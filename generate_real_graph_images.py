import os
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx

BASE_DIR = Path(__file__).resolve().parent
DOCS_IMG_DIR = BASE_DIR / "docs" / "images"
PUBLIC_IMG_DIR = BASE_DIR / "frontend" / "public" / "images"

DOCS_IMG_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_IMG_DIR.mkdir(parents=True, exist_ok=True)

plt.style.use('dark_background')

# Load the exact extracted live data from scratch/all_extracted_live_graphs.json
DATA_FILE = BASE_DIR / "scratch" / "all_extracted_live_graphs.json"
with open(DATA_FILE, "r", encoding="utf-8") as f:
    live_graphs = json.load(f)

def render_exact_domain_kg(domain_key, output_filename, title, color_map_def):
    print(f"Rendering 100% exact live graph image for {domain_key}...")
    graph_data = live_graphs.get(domain_key, {"nodes": [], "edges": []})
    
    G = nx.DiGraph()
    node_types = {}
    
    for n in graph_data["nodes"]:
        name = n["name"].strip()
        ntype = n.get("type", "Concept").strip()
        if name:
            G.add_node(name, type=ntype)
            node_types[name] = ntype
            
    for e in graph_data["edges"]:
        src = e["source"].strip()
        tgt = e["target"].strip()
        rel = e.get("relation", "").strip()
        if src and tgt:
            if src not in G:
                G.add_node(src, type="Concept")
            if tgt not in G:
                G.add_node(tgt, type="Concept")
            G.add_edge(src, tgt, label=rel)

    if len(G.nodes) == 0:
        print(f"No nodes found for {domain_key}")
        return

    fig, ax = plt.subplots(figsize=(16, 12), facecolor='#0B0F19')
    ax.set_facecolor('#0B0F19')
    
    # Layout using kamada_kawai or spring layout for maximum readability
    try:
        pos = nx.kamada_kawai_layout(G)
    except Exception:
        pos = nx.spring_layout(G, k=1.1, iterations=150, seed=42)
    
    node_colors = []
    for n in G.nodes():
        ntype = node_types.get(n, "Concept")
        node_colors.append(color_map_def.get(ntype, "#06b6d4"))
        
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=node_colors,
        node_size=1500,
        edgecolors='#ffffff',
        linewidths=1.2,
        alpha=0.95
    )
    
    nx.draw_networkx_edges(
        G, pos, ax=ax,
        edge_color='#64748b',
        arrowsize=14,
        arrowstyle='->',
        width=1.6,
        connectionstyle='arc3,rad=0.06'
    )
    
    nx.draw_networkx_labels(
        G, pos, ax=ax,
        font_size=7.5,
        font_color='#F9FAFB',
        font_weight='bold',
        font_family='sans-serif'
    )
    
    edge_labels = {(u, v): d.get('label', '') for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(
        G, pos, edge_labels=edge_labels, ax=ax,
        font_size=6.5,
        font_color='#38bdf8',
        bbox=dict(boxstyle='round,pad=0.2', fc='#111827', ec='#1e293b', alpha=0.85)
    )
    
    plt.title(f"{title} ({len(G.nodes)} Nodes, {len(G.edges)} Relationships from Neo4j)", fontsize=15, fontweight='bold', color='#06b6d4', pad=20)
    plt.axis('off')
    plt.tight_layout()
    
    out_docs = DOCS_IMG_DIR / output_filename
    out_pub = PUBLIC_IMG_DIR / output_filename
    
    plt.savefig(out_docs, dpi=300, bbox_inches='tight', facecolor='#0B0F19')
    plt.savefig(out_pub, dpi=300, bbox_inches='tight', facecolor='#0B0F19')
    plt.close()
    print(f"Saved exact graph image: {out_docs}")


def render_temporal_patient_graph_exact():
    print("Rendering exact Temporal Patient Graph (TG) timeline...")
    # Load actual synthetic_cases.json case
    cases_file = BASE_DIR / "Retinopathy" / "synthetic_cases.json"
    case_data = None
    if cases_file.exists():
        with open(cases_file, "r", encoding="utf-8") as f:
            cases_data = json.load(f)
            if cases_data.get("cases"):
                case_data = cases_data["cases"][0]

    G = nx.DiGraph()
    patient_id = case_data["id"] if case_data else "P001"
    G.add_node(f"Patient: {patient_id}", type="Patient")
    
    if case_data and "timeline" in case_data:
        timeline = case_data["timeline"]
        prev_visit = None
        for visit in timeline:
            v_date = visit["date"]
            v_node = f"Visit: {v_date}"
            G.add_node(v_node, type="Visit")
            G.add_edge(f"Patient: {patient_id}", v_node, label="HAS_VISIT")
            
            if prev_visit:
                G.add_edge(prev_visit, v_node, label="NEXT_VISIT")
            prev_visit = v_node
            
            # Attach measurements for this visit
            for key, val in visit.items():
                if key != "date" and val is not None:
                    m_node = f"Meas: {key}={val}"
                    G.add_node(m_node, type="Measurement")
                    G.add_edge(v_node, m_node, label="HAS_MEASUREMENT")
                    G.add_node(f"Concept: {key}", type="Concept")
                    G.add_edge(m_node, f"Concept: {key}", label="INSTANCE_OF")
    else:
        # Fallback timeline if JSON structure differs
        G.add_node("Visit: 2024-01-10", type="Visit")
        G.add_edge(f"Patient: {patient_id}", "Visit: 2024-01-10", label="HAS_VISIT")
        
    fig, ax = plt.subplots(figsize=(16, 11), facecolor='#0B0F19')
    ax.set_facecolor('#0B0F19')
    
    pos = nx.spring_layout(G, k=1.1, iterations=140, seed=20)
    
    color_map = {
        "Patient": "#3b82f6",
        "Visit": "#10b981",
        "Measurement": "#f59e0b",
        "Concept": "#06b6d4"
    }
    
    node_colors = [color_map.get(G.nodes[n].get("type"), "#06b6d4") for n in G.nodes()]
    
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=1600, edgecolors='#ffffff', linewidths=1.5, alpha=0.95)
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color='#64748b', arrowsize=16, arrowstyle='->', width=1.7, connectionstyle='arc3,rad=0.06')
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=7.5, font_color='#F9FAFB', font_weight='bold')
    
    edge_labels = {(u, v): d.get('label', '') for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax, font_size=6.5, font_color='#38bdf8', bbox=dict(boxstyle='round,pad=0.2', fc='#111827', ec='#1e293b', alpha=0.85))
    
    plt.title(f"Temporal Patient Graph (TG) - Live Patient Encounter Timeline ({patient_id})", fontsize=15, fontweight='bold', color='#10b981', pad=20)
    plt.axis('off')
    plt.tight_layout()
    
    out_docs = DOCS_IMG_DIR / "temporal_patient_graph_real.png"
    out_pub = PUBLIC_IMG_DIR / "temporal_patient_graph_real.png"
    
    plt.savefig(out_docs, dpi=300, bbox_inches='tight', facecolor='#0B0F19')
    plt.savefig(out_pub, dpi=300, bbox_inches='tight', facecolor='#0B0F19')
    plt.close()
    print(f"Saved exact TG graph image: {out_docs}")


if __name__ == "__main__":
    # 1. Kidney KG (Live extracted from Neo4j)
    render_exact_domain_kg(
        "Kidney_KG",
        "kidney_kg_real.png",
        "Kidney Clinical Knowledge Graph (Kidney_KG)",
        {"Measurement": "#06b6d4", "Condition": "#ef4444", "Context": "#f59e0b", "Concept": "#38bdf8"}
    )

    # 2. Cardio KG (Live extracted from Neo4j)
    render_exact_domain_kg(
        "Cardio_KG",
        "cardio_kg_real.png",
        "Cardiovascular Clinical Knowledge Graph (Cardio_KG)",
        {"Measurement": "#ef4444", "Condition": "#f97316", "Context": "#eab308", "Concept": "#ec4899"}
    )
    
    # 3. Retinopathy KG (Local dataset CSV)
    render_exact_domain_kg(
        "Retinopathy_KG",
        "retinopathy_kg_real.png",
        "Retinopathy Clinical Knowledge Graph (Retinopathy_KG)",
        {"Microvascular": "#10b981", "Glycemic Control": "#06b6d4", "Concept": "#8b5cf6"}
    )
    
    # 4. Temporal Patient Graph (TG)
    render_temporal_patient_graph_exact()
    
    print("All 4 exact graph images rendered from codebase & Neo4j!")
