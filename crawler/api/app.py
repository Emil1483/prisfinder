from flask import Flask

from routes.provisioners import provisioners_bp
from routes.products import products_bp
from routes.finn import finn_bp

app = Flask(__name__)

app.register_blueprint(provisioners_bp)
app.register_blueprint(products_bp)
app.register_blueprint(finn_bp)


if __name__ == "__main__":
    app.run(debug=True, port=8080)
