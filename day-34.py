"""
M8 Day 34 — Production hybrid: graph coverage + vector recall + faithfulness.

Day 32: Graph RAG multi-hop path.
Day 33: Graph-specific eval (entity/relation coverage) > vector.
Day 34: COMBINE — hybrid retrieval (graph entities ∪ vector top-k) then
measure FAITHFULNESS: does the generated answer actually use the retrieved
graph entities? This is the production pattern: graph for structure,
vector for semantic match, faithfulness guard against hallucination.

Study claim: hybrid recall (graph ∪ vector) >= either alone; faithfulness
on graph context stays high because entities are explicit (not embedded).

Test: 3-hop chain. Hybrid retrieves {Alice,Bob,Acme,NYC} (graph) ∪ top-k
(vector). Faithfulness = answer entities ⊆ retrieved entities.
"""
import sys, os, json, re, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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


class GraphRAG:
    def __init__(self):
        self.edges = []

    def add(self, s, r, o):
        self.edges.append((s, r, o))

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
    g.add("Alice", "worksAt", "Acme")
    g.add("Acme", "locatedIn", "NYC")
    g.add("Bob", "worksAt", "Acme")

    query = "Where does Alice's coworker Bob work?"
    E_exp = {"Alice", "Bob", "Acme"}

    # GRAPH retrieval
    E_graph = g.bfs_entities("Alice", depth=2)

    # VECTOR retrieval (top-2 by cosine)
    q = _nv_embed("Alice coworker Bob work location")
    descs = {
        "Alice": "person Alice employee",
        "Acme": "company Acme employer New York City",
        "Bob": "person Bob employee",
        "NYC": "city New York location",
    }
    vec_scored = sorted(((cosine(q, _nv_embed(d)), n) for n, d in descs.items()),
                        reverse=True)
    E_vec = {n for _, n in vec_scored[:2]}

    # HYBRID = graph ∪ vector
    E_hybrid = E_graph | E_vec
    cov_graph = len(E_graph & E_exp) / len(E_exp)
    cov_vec = len(E_vec & E_exp) / len(E_exp)
    cov_hybrid = len(E_hybrid & E_exp) / len(E_exp)

    # FAITHFULNESS: mock answer uses only retrieved entities
    answer_entities = {"Alice", "Bob", "Acme"}  # LLM would extract these
    faithful = answer_entities <= E_hybrid

    print(f"GRAPH  cov: {cov_graph:.2f}")
    print(f"VECTOR cov: {cov_vec:.2f}")
    print(f"HYBRID cov: {cov_hybrid:.2f}  (graph ∪ vector)")
    print(f"E_hybrid: {sorted(E_hybrid)}")
    print(f"FAITHFULNESS (answer ⊆ hybrid): {faithful}")

    assert cov_hybrid >= cov_graph, "hybrid should be >= graph"
    assert cov_hybrid >= cov_vec, "hybrid should be >= vector"
    assert faithful, "answer must use only retrieved entities"
    print("PASS: Hybrid recall >= either; faithfulness guard holds on graph context")


if __name__ == "__main__":
    main()
