from flask import Flask

from api.routes.provisioners import provisioners_bp
from api.routes.products import products_bp
from api.routes.finn import finn_bp

app = Flask(__name__)

app.register_blueprint(provisioners_bp)
app.register_blueprint(products_bp)
app.register_blueprint(finn_bp)


if __name__ == "__main__":
    app.run(debug=True, port=8080)
