from tests.test_website.product import Product


def _link_elements(links: list[str]):
    result = ""
    for link in links:
        href = link if "http" in link else f"/{link}"
        result += f'<li><a href="{href}">{link}</a></li>'
    return result


def html_with_links(links: list[str]):
    return f"<html>{_link_elements(links)}</html>"


def product_html(links: list[str], product: Product):
    return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Product Page</title>
            <script type="application/ld+json">
            {{
                "@context": "https://schema.org",
                "@type": "Product",
                "name": "{product.name}",
                "image": [
                    "{product.image}"
                ],
                "description": "{product.description}",
                "sku": "{product.sku}",
                "mpn": "{product.mpn}",
                "gtin13": "{product.gtin13}",
                "brand": {{
                    "@type": "Brand",
                    "name": "{product.brand}"
                }},
                "offers": {{
                    "@type": "Offer",
                    "url": "https://www.power.no/tv-og-lyd/hodetelefoner/true-wireless-hodetelefoner/samsung-galaxy-buds2-pro-true-wireless-bora-purple/p-1646111/",
                    "priceCurrency": "NOK",
                    "price": {product.price},
                    "availability": "https://schema.org/OutOfStock",
                    "availabilityStarts": "08.09.2023"
                }}
            }}
            </script>
        </head>
        <body>
            <h1>{product.name}</h1>
            <img src="{product.image}" alt="{product.name}">
            <p>{product.description}</p>
            <p>Price: {product.price}</p>
            <p>Brand: {product.brand}</p>
            <p>Sku: {product.sku}</p>
            <p>Mpn: {product.mpn}</p>
            <p>Gtin13: {product.gtin13}</p>
            {_link_elements(links)}
        </body>
        </html>
    """
