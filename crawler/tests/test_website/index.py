from flask import Flask, redirect

from tests.test_website.html import html_with_links, product_html
from tests.test_website.graph import build_endpoints_graph
from tests.test_website.product import test_products

app = Flask(__name__)

g = build_endpoints_graph()


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
            yield optimize(path)

    destination = nested_route.split("/")[-1]
    if "p-" in destination:
        index = int(str(destination).split("-")[-1])
        return product_html([*gen_links()], test_products[index])

    return html_with_links([*gen_links()])


if __name__ == "__main__":
    app.run(debug=True, port=80)
