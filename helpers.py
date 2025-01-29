import requests
from flask import redirect, session, render_template
from functools import wraps

def apology(message, code=400):
    """Render an apology to the user."""
    return render_template("apology.html", top=code, bottom=escape(message)), code

def get_coin_name_from_api(symbol):
    """
    Lấy tên coin từ Binance API dựa trên symbol.
    """
    url = "https://api.binance.com/api/v3/exchangeInfo"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        for coin in data["symbols"]:
            if coin["symbol"] == symbol:
                return coin["baseAsset"]  # Tên coin từ baseAsset
    except requests.RequestException as e:
        print(f"Lỗi khi gọi API: {e}")
    return None

def escape(s):
    """Escape special characters."""
    for old, new in [
        ("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
        ("%", "~p"), ("#", "~h"), ("/", "~s"), ('"', "''"),
    ]:
        s = s.replace(old, new)
    return s

def login_required(f):
    """Ensure user is logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def usd(value):
    if value is None:
        return "N/A"
    return f"${value:,.2f}"

def get_user_cash(db, user_id):
    """Get the cash balance of a user."""
    rows = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
    return rows[0]["cash"] if rows else 0

def get_user_holdings_with_names(db, user_id):
    # Truy vấn holdings từ bảng transactions
    rows = db.execute("""
        SELECT symbol, SUM(amount) AS amount
        FROM transactions
        WHERE user_id = ?
        GROUP BY symbol
        HAVING amount > 0
    """, user_id)

    holdings = []
    for row in rows:
        symbol = row["symbol"]
        amount = float(row["amount"]) 

        coin_name = get_coin_name_from_api(symbol) or "Unknown"

        price = get_crypto_price(symbol)
        price = float(price) if price else 0


        total = amount * price

        holdings.append({
            "name": coin_name,
            "symbol": symbol,
            "amount": amount,
            "price": price,  
            "total": total, 
        })

    return holdings


def get_user_holdings(db, user_id):
    """Get the holdings of a user."""
    rows = db.execute("""
        SELECT symbol, SUM(amount) AS total
        FROM transactions
        WHERE user_id = ?
        GROUP BY symbol
        HAVING total > 0
    """, user_id)
    return [{"symbol": row["symbol"], "total": row["total"]} for row in rows]

def get_crypto_price(symbol):
    """Fetch the price of a cryptocurrency."""
    url = "https://api.binance.com/api/v3/ticker/price"
    response = requests.get(url, params={"symbol": symbol})
    if response.status_code == 200:
        return float(response.json()["price"])
    return None

def validate_user_input(request):
    """Validate user input for coin and amount."""
    coin = request.form.get("coin").strip().upper()
    amount = request.form.get("amount")
    if not coin:
        return None, None, "Vui lòng nhập mã coin."
    try:
        amount = float(amount)
        if amount <= 0:
            return None, None, "Số lượng phải lớn hơn 0."
    except ValueError:
        return None, None, "Số lượng không hợp lệ."
    return coin, amount, None

def update_cash(db, cash, user_id):
    try: 
        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", cash, user_id)
    except Exception as e:
        db.execute("ROLLBACK;")
        return {"error": str(e)}

def handle_transaction(db, user_id, symbol, amount, price, transaction_type):
    """Handle a buy or sell transaction."""
    total_cost = amount * price
    try:
        db.execute("BEGIN TRANSACTION;")
        db.execute("""
            INSERT INTO transactions (user_id, symbol, transaction_type, amount, price, total_cost)
            VALUES (?, ?, ?, ?, ?, ?)
        """, user_id, symbol, transaction_type, amount, price, total_cost)
        update_cash(db, -total_cost, user_id)    
        db.execute("COMMIT;")
        return {"total_cost": total_cost}
    except Exception as e:
        db.execute("ROLLBACK;")
        return {"error": str(e)}
