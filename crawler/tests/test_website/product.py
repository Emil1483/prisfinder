from dataclasses import dataclass


@dataclass(order=True, frozen=True)
class Product(object):
    name: str
    image: str
    description: str
    sku: str
    mpn: str
    gtin13: str
    brand: str
    price: float


test_products = [
    Product(
        name="Smartphone X",
        image="smartphone_x.jpg",
        description="A powerful and sleek smartphone with advanced features.",
        sku="SPX123",
        mpn="MPN456",
        gtin13="1234567890123",
        brand="TechCo",
        price=599.99,
    ),
    Product(
        name="Laptop Pro",
        image="laptop_pro.jpg",
        description="High-performance laptop for professionals and creatives.",
        sku="LP456",
        mpn="MPN789",
        gtin13="9876543210123",
        brand="TechGenius",
        price=1299.99,
    ),
    Product(
        name="Wireless Earbuds",
        image="earbuds.jpg",
        description="True wireless earbuds with noise-cancellation technology.",
        sku="WB789",
        mpn="MPN123",
        gtin13="5432109876543",
        brand="AudioTech",
        price=129.95,
    ),
    Product(
        name="Fitness Tracker",
        image="fitness_tracker.jpg",
        description="Track your health and fitness goals with this advanced tracker.",
        sku="FT456",
        mpn="MPN789",
        gtin13="7890123456789",
        brand="FitLife",
        price=49.99,
    ),
    Product(
        name="Coffee Maker",
        image="coffee_maker.jpg",
        description="Brew the perfect cup of coffee with this easy-to-use coffee maker.",
        sku="CM123",
        mpn="MPN456",
        gtin13="2345678901234",
        brand="BrewMaster",
        price=79.99,
    ),
    Product(
        name="Smart TV",
        image="smart_tv.jpg",
        description="Immerse yourself in stunning visuals with this 4K smart TV.",
        sku="TV789",
        mpn="MPN123",
        gtin13="6789012345678",
        brand="VisionTech",
        price=899.99,
    ),
    Product(
        name="Gaming Mouse",
        image="gaming_mouse.jpg",
        description="Enhance your gaming experience with this high-precision gaming mouse.",
        sku="GM456",
        mpn="MPN789",
        gtin13="3456789012345",
        brand="GameFusion",
        price=59.99,
    ),
    Product(
        name="Portable Speaker",
        image="speaker.jpg",
        description="Take the party with you with this portable Bluetooth speaker.",
        sku="PS123",
        mpn="MPN456",
        gtin13="4567890123456",
        brand="SoundWave",
        price=89.95,
    ),
    Product(
        name="Wireless Router",
        image="router.jpg",
        description="Experience fast and reliable internet with this advanced wireless router.",
        sku="WR789",
        mpn="MPN123",
        gtin13="5678901234567",
        brand="NetConnect",
        price=149.99,
    ),
    Product(
        name="Digital Camera",
        image="camera.jpg",
        description="Capture memories in stunning detail with this high-resolution digital camera.",
        sku="DC456",
        mpn="MPN789",
        gtin13="6789012345678",
        brand="PhotoPro",
        price=399.99,
    ),
]
