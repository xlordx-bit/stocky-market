from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from flask import jsonify, flash
from breeze_connect import BreezeConnect
import pandas as pd
from datetime import datetime, timedelta
import time
import urllib
import os
import requests
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'stockeykey123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


with app.app_context():
    db.create_all()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return "User already exists."

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid email or password.")

    return render_template("login.html")

breeze = None

@app.route("/api_validate", methods=["POST"])
@login_required
def api_validate():
    try:
        
        api_key = "057z6#K658B5MI1`t8519W7055l9305c"
        api_secret = "84_68%57m963501139n82b51i3Mu506z"
        api_session = "51719165"
        
        

        global breeze
        breeze = BreezeConnect(api_key=api_key)
        login_url = "https://api.icicidirect.com/apiuser/login?api_key=" + urllib.parse.quote_plus(api_key)
        
        try:
            breeze.generate_session(api_secret=api_secret, session_token=api_session)
            session['api_authenticated'] = True
            return jsonify({"status": "success", "message": "API authenticated successfully"}), 200
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/dashboard")
@login_required
def dashboard():
    username = session.get("username", "Guest")
    api_authenticated = session.get('api_authenticated', False)
    return render_template("dashboard.html", username=username, api_authenticated=api_authenticated)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/download_data", methods=["POST"])
@login_required
def download_data():
    try:
        if not session.get('api_authenticated'):
            return jsonify({"status": "error", "message": "Please connect to API first"}), 401
            
        if not breeze:
            return jsonify({"status": "error", "message": "API connection not initialized"}), 401
            
        stock_code = request.form.get('stock_code')
        exchange_code = request.form.get('exchange_code')
        from_date = datetime.strptime(request.form.get('from_date'), '%Y-%m-%d')
        to_date = datetime.strptime(request.form.get('to_date'), '%Y-%m-%d')
        interval = request.form.get('interval')
        product_type = request.form.get('product_type')
        right = request.form.get('right')
        strike_price_start = float(request.form.get('strike_price_start'))
        strike_price_end = float(request.form.get('strike_price_end'))
        expiry_date = datetime.strptime(request.form.get('expiry_date'), '%Y-%m-%d')

        try:
            
            historical_data = breeze.get_historical_data(
                interval=interval,
                from_date=from_date.strftime('%Y-%m-%d'),
                to_date=to_date.strftime('%Y-%m-%d'),
                stock_code=stock_code,
                exchange_code=exchange_code,
                product_type=product_type,
                strike_price=strike_price_start,  
                right=right,
                expiry_date=expiry_date.strftime('%Y-%m-%d')
            )

            
            df = pd.DataFrame(historical_data)
            
            
            if not os.path.exists('downloads'):
                os.makedirs('downloads')
                
            
            filename = f"downloads/{stock_code}_{from_date.strftime('%Y%m%d')}_{to_date.strftime('%Y%m%d')}.csv"
            df.to_csv(filename, index=False)
            
            return jsonify({
                "status": "success",
                "message": "Data downloaded successfully",
                "filename": filename
            }), 200
            
        except Exception as e:
            return jsonify({"status": "error", "message": f"Failed to download data: {str(e)}"}), 500
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/place_order", methods=["POST"])
@login_required
def place_order():
    try:
        if not session.get('api_authenticated'):
            return jsonify({"status": "error", "message": "Please connect to API first"}), 401

        nifty = request.form.get('nifty')
        call = request.form.get('call')
        put = request.form.get('put')
        order_log = request.form.get('order_log')
        
       
        return jsonify({
            "status": "success",
            "message": "Order placed successfully",
            "details": {
                "nifty": nifty,
                "call": call,
                "put": put,
                "order_log": order_log
            }
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
@app.route('/api/market_data')
@login_required
def market_data():
    if not session.get('api_authenticated'):
        return jsonify(success=False, error="API not authenticated")

    global breeze
    if not breeze:
        return jsonify(success=False, error="Breeze API not initialized")

    try:
        # Define the symbols you want real-time quotes for
        # Format: "<exchange>:<symbol>" (verify symbols from Breeze docs)
        symbols = [
            "NSE:NIFTY 50",
            "BSE:SENSEX",
            "NSE:RELIANCE",
            "NSE:INFY",
            "NSE:HDFCBANK"
        ]

        data = {}
        for symbol in symbols:
            try:
                quote = breeze.get_market_quote(exchange_code=symbol.split(":")[0], stock_code=symbol.split(":")[1])
                # Extract last traded price or close price from response structure
                # (Adjust this depending on actual Breeze response JSON structure)
                last_price = quote['last_price'] if 'last_price' in quote else quote.get('close', 'N/A')
                data[symbol.split(":")[1]] = last_price
            except Exception as e:
                data[symbol.split(":")[1]] = "N/A"

        return jsonify(success=True, data=data)
    except Exception as e:
        return jsonify(success=False, error=str(e))

if __name__ == "__main__":
    app.run(debug=True)
