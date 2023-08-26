class Graph:
    def __init__(self):
        self.graph = {}

    @property
    def nodes(self) -> list[str]:
        return [*self.graph.keys()]

    def add_node(self, node):
        if node not in self.graph:
            self.graph[node] = []

    def add_edge(self, node1, node2, two_way=True):
        if node1 in self.graph and node2 in self.graph:
            if node2 not in self.graph[node1]:
                self.graph[node1].append(node2)
            if two_way:
                self.add_edge(node2, node1, two_way=False)

    def get_neighbors(self, node):
        if node in self.graph:
            return self.graph[node]
        else:
            return []

    def __str__(self):
        return str(self.graph)


def build_endpoints_graph():
    g = Graph()

    g.add_node("home")
    g.add_node("about")
    g.add_node("tips")
    g.add_node("reviews")
    g.add_node("categories")
    g.add_node("products")

    g.add_edge("home", "about")
    g.add_edge("home", "tips")
    g.add_edge("home", "reviews")
    g.add_edge("home", "categories")
    g.add_edge("home", "products")

    for i in range(5):
        g.add_node(f"category{i}")
        g.add_edge(f"categories", f"category{i}")

    for i in range(5):
        g.add_node(f"p-{i}")
        g.add_edge(f"products", f"p-{i}")

    for i in range(3):
        g.add_node(f"review{i}")
        g.add_edge(f"reviews", f"review{i}")

    g.add_node(f"https://abc.xyz")
    g.add_edge("about", "https://abc.xyz")

    g.add_node(f"https://google.com")
    g.add_edge("tips", "https://google.com")

    g.add_node(f"p-5")
    g.add_edge(f"p-1", f"p-5")

    g.add_node(f"p-6")
    g.add_edge(f"review2", f"p-6")

    g.add_node(f"p-7")
    g.add_edge(f"p-6", f"p-7")

    g.add_node(f"p-8")
    g.add_edge(f"about", f"p-8")

    g.add_node(f"p-9")
    g.add_edge(f"category1", f"p-9")

    for node in g.nodes:
        if node != "home":
            g.add_edge(node, "home", two_way=False)

    return g
