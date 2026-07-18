"""
M8 Day 33 — Graph-specific eval: entity/relation coverage.

Day 32 built Graph RAG (multi-hop path). Today we evaluate the GRAPH's
unique value: can it retrieve the ENTITIES + RELATIONS a query needs,
which pure vector similarity cannot surface?

Metric (graph coverage):
  coverage_E = |E_ret ∩ E_exp| / |E_exp|
  coverage_R = |R_ret ∩ R_exp| / |R_exp|
This is graph-specific — vector RAG has no entity/relation notion.

Study claim: Graph RAG coverage_E/R > vector-only for multi-hop queries,
because the graph stores explicit edges the embedder cannot encode.

Test: 3-hop fact chain. Query needs 2 entities + 1 relation. Graph returns
both via edge traversal; vector (cosine) may miss the 2nd entity.
"""
import sys, os, json, re, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# load .env (same pattern as Day 32)
_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", ".env")
if not os.path.exists(_env):
    _env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
if os.path.exists(_env):
    for _l in open(_env, encoding="utf-8", errors="replace"):
        _l = _l.strip()
        if _l and not _l.startswith("#") and "=" in _l:
            _k, _v = _l.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())


def _nv_embed(text: str, model: str = "nvidia/nemotron-3-embed-1b") -> list:
    """Local NVIDIA embed (curl). Sandbox-safe (no import providers)."""
    key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if not key:
        raise RuntimeError("NVIDIA_API_KEY missing")
    url = "https://integrate.api.nvidia.com/v1/embeddings"
    payload = json.dumps({"input": text, "model": model,
                          "input_type": "passage", "encoding_format": "float"})
    cmd = ["curl", "-s", "--max-time", "30", "-X", "POST", url,
           "-H", f"Authorization: Bearer {key}",
           "-H", "Content-Type: application/json", "-d", payload]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
    return json.loads(out.stdout)["data"][0]["embedding"]


# ---- tiny graph store ------------------------------------------------------
class GraphRAG:
    def __init__(self):
        self.edges = []  # (subj, rel, obj)

    def add(self, s, r, o):
        self.edges.append((s, r, o))

    def entities(self):
        e = set()
        for s, r, o in self.edges:
            e.add(s); e.add(o)
        return e

    def relations_of(self, entity):
        return [(r, o) for s, r, o in self.edges if s == entity] + \
               [(f"inv:{r}", s) for s, r, o in self.edges if o == entity]

    def bfs_entities(self, start, depth=2):
        seen, frontier = set(), [start]
        for _ in range(depth):
            nxt = []
            for e in frontier:
                for s, r, o in self.edges:
                    if s == e and o not in seen:
                        seen.add(o); nxt.append(o)
                    if o == e and s not in seen:
                        seen.add(s); nxt.append(s)
            frontier = nxt
        return seen


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def main():
    g = GraphRAG()
    # 3-hop: Alice→worksAt→Acme→locatedIn→NYC ; Bob→worksAt→Acme
    g.add("Alice", "worksAt", "Acme")
    g.add("Acme", "locatedIn", "NYC")
    g.add("Bob", "worksAt", "Acme")

    # ---- expected answer for query "Where does Alice's coworker Bob work?" ----
    # needs entities {Alice, Bob, Acme} + relation worksAt
    E_exp = {"Alice", "Bob", "Acme"}
    R_exp = {"worksAt"}

    # ---- GRAPH retrieval (2-hop from Alice) ----
    E_ret_graph = g.bfs_entities("Alice", depth=2)
    R_ret_graph = set()
    for e in E_ret_graph:
        R_ret_graph |= {r for r, _ in g.relations_of(e)}

    cov_E_graph = len(E_ret_graph & E_exp) / len(E_exp)
    cov_R_graph = len(R_ret_graph & R_exp) / len(R_exp)

    # ---- VECTOR retrieval (cosine of query vs entity descriptions) ----
    q = _nv_embed("Alice coworker Bob work location")
    descs = {
        "Alice": "person Alice employee",
        "Acme": "company Acme employer New York City",
        "Bob": "person Bob employee",
        "NYC": "city New York location",
    }
    scored = sorted(((cosine(q, _nv_embed(d)), n) for n, d in descs.items()),
                    reverse=True)
    # vector top-2 as "retrieved entities"
    E_ret_vec = {n for _, n in scored[:2]}
    cov_E_vec = len(E_ret_vec & E_exp) / len(E_exp)

    # ---- eval report ----
    print(f"GRAPH  coverage_E: {cov_E_graph:.2f}  coverage_R: {cov_R_graph:.2f}")
    print(f"VECTOR coverage_E (top2): {cov_E_vec:.2f}")
    print(f"E_ret_graph: {sorted(E_ret_graph)}")
    print(f"E_ret_vec  : {sorted(E_ret_vec)}")

    assert cov_E_graph >= cov_E_vec, "graph should cover >= vector for multi-hop"
    assert cov_R_graph == 1.0, "graph must retrieve worksAt relation"
    print("PASS: Graph RAG entity/relation coverage >= vector for multi-hop query")


if __name__ == "__main__":
    main()
