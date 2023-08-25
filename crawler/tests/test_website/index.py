from flask import Flask, redirect

from tests.test_website.html import html_with_links, product_html
from tests.test_website.graph import Graph
from tests.test_website.product import test_products

app = Flask(__name__)


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


@app.route("/", methods=["GET"])
def home():
    return redirect("/home")


@app.route("/<path:nested_route>")
def dynamic_route(nested_route: str):
    def optimize(route: str):
        components = route.split("/")
        optimized_components = ["home"]
        destination = components[-1]

        for current_node in components:
            if current_node == "home":
                optimized_components = ["home"]
                continue

            optimized_components.append(current_node)

            if current_node == destination:
                break

        optimized_path = "/".join(optimized_components)
        return optimized_path

    def gen_links():
        components = nested_route.split("/")
        neighbors = g.get_neighbors(components[-1])
        for neighbor in neighbors:
            if "http" in neighbor:
                yield neighbor
                continue

            path = f"{nested_route}/{neighbor}"
            print(path)
            yield optimize(path)

    destination = nested_route.split("/")[-1]
    if "p-" in destination:
        index = int(str(destination).split("-")[-1])
        return product_html([*gen_links()], test_products[index])

    return html_with_links([*gen_links()])


if __name__ == "__main__":
    app.run(debug=True, port=3000)
