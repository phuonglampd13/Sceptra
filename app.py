import os
from cs50 import SQL
from flask import Flask, redirect, render_template, request, session, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import (
    login_required,
    usd,
    get_user_cash,
    get_user_holdings_with_names,
    get_crypto_price,
    handle_transaction,
    validate_user_input,
    update_cash,
)

# Configure application
app = Flask(__name__)

# Configure custom filter for currency formatting
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure database connection
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


### ROUTES ###

# Index Route
@app.route("/")
@login_required
def index():
    """Display user's portfolio"""
    cash = get_user_cash(db, session["user_id"])
    holdings = get_user_holdings_with_names(db, session["user_id"])
    return render_template("index.html", holdings=holdings, cash=cash)



# TradingView Route
@app.route("/tradingview")
def tradingview():
    """Display TradingView widget"""
    return render_template("tradingview.html")


# Buy Route
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Handle buy transactions"""
    user_id = session["user_id"]
    cash = get_user_cash(db, user_id)

    if request.method == "POST":
        # Validate input
        coin, amount, error = validate_user_input(request)
        if error:
            return render_template("buy.html", cash=cash, messages=[error])

        # Fetch crypto price
        price = get_crypto_price(coin)
        if price is None:
            return render_template("buy.html", cash=cash, messages=["Không thể lấy giá coin."])

        # Handle transaction
        result = handle_transaction(db, user_id, coin, amount, price, transaction_type="BUY")
        if "error" in result:
            return render_template("buy.html", cash=cash, messages=[result["error"]])

        # Update cash and show success message
        cash -= result["total_cost"]
        return render_template("buy.html", cash=cash, messages=["Giao dịch thành công!"])

    return render_template("buy.html", cash=cash)


# Sell Route
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Handle sell transactions"""
    user_id = session["user_id"]
    cash = get_user_cash(db, user_id)
    holdings = get_user_holdings_with_names(db, user_id)
    if request.method == "POST":
        # Validate input
        coin, amount, error = validate_user_input(request)
        if error:
            return render_template("sell.html", cash=cash, holdings=holdings, messages=[error])

        # Fetch crypto price
        price = get_crypto_price(coin)
        if price is None:
            return render_template("sell.html", cash=cash, holdings=holdings, messages=["Không thể lấy giá coin."])

        # Check if user has enough coin to sell
        user_coin = next((h for h in holdings if h["symbol"] == coin), None)
        if not user_coin or user_coin["amount"] < amount:
            return render_template("sell.html", cash=cash, holdings=holdings, messages=[f"Số lượng {coin} không đủ để bán."])

        # Handle transaction
        result = handle_transaction(db, user_id, coin, -amount, price, transaction_type="SELL")
        if "error" in result:
            return render_template("sell.html", cash=cash, holdings=holdings, messages=[result["error"]])

        # Update cash and show success message
        holdings = get_user_holdings_with_names(db, user_id)
        cash -= result["total_cost"]
        return render_template("sell.html", cash=cash, holdings=holdings, messages=["Giao dịch thành công!"])

    return render_template("sell.html", cash=cash, holdings=holdings)

@app.route("/history")
@login_required
def history():
    """transactions"""
    user_id = session["user_id"]

    transactions = db.execute("""
        SELECT * FROM transactions WHERE user_id = ?
    """, user_id)      

    return render_template("history.html", transactions=transactions)


@app.route("/add_cash", methods=["GET", "POST"])
@login_required
def add_cash():
    user_id = session["user_id"]
    cash = get_user_cash(db, user_id)
    
    if request.method == "GET":
        return render_template("add_cash.html", cash=cash)
    else:
        amount = float(request.form.get("amount"))
        
        try:
            # Update the user's cash in the database
            update_cash(db, amount, session["user_id"])
            # Get the updated cash balance after the addition
            cash = get_user_cash(db, user_id)  # Fetch updated cash balance
            return render_template("add_cash.html", cash=cash)
        except Exception as e:
            # Handle any database errors or unexpected issues
            messages = ["Lỗi trong quá trình xử lý. Vui lòng thử lại."]
            return render_template("add_cash.html", cash=cash, messages=messages)


@app.route("/cash_out", methods=["GET", "POST"])
@login_required
def cash_out():
    user_id = session["user_id"]
    cash = get_user_cash(db, user_id)
    
    if request.method == "GET":
        return render_template("cash_out.html", cash=cash)
    else:
        amount = float(request.form.get("amount"))
        print(cash, amount)
        
        # Check if there's enough balance
        if amount > cash:
            messages = ["Số dư tài khoản không đủ"]
            return render_template("cash_out.html", cash=cash, messages=messages)
        
        try:
            # Update the user's cash in the database
            update_cash(db, -amount, session["user_id"])
            cash -= amount  # Subtract the amount from the available cash
            return render_template("cash_out.html", cash=cash)
        except Exception as e:
            # Handle any database errors or unexpected issues
            messages = ["Lỗi trong quá trình xử lý. Vui lòng thử lại."]
            return render_template("cash_out.html", cash=cash, messages=messages)


# Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return render_template("login.html", messages=["Tên người dùng hoặc mật khẩu không hợp lệ."])

        session["user_id"] = rows[0]["id"]
        return redirect("/")

    return render_template("login.html")


# Register Route
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Validate input
        if password != confirmation:
            return render_template("register.html", messages=["Mật khẩu không khớp."])

        # Check if username exists
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if rows:
            return render_template("register.html", messages=["Tên người dùng đã tồn tại."])

        # Insert new user
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, generate_password_hash(password))
        return render_template("register.html", messages=["Đăng ký thành công!"])

    return render_template("register.html")


# Logout Route
@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    return redirect("/")


if __name__ == '__main__':
    app.run(debug=True)
