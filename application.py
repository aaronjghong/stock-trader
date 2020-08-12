import os
import time

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():

    # Gets portfolio, looks up current prices, and sends it to index.html
    portfolio = db.execute("SELECT * FROM portfolio WHERE id = :id", id = session["user_id"])
    sum = 0
    for row in portfolio:
        row['price'] = int(row['amount']) * float(lookup(row['stock'])['price'])
        sum += row['price']
        row['price'] = round(row['price'],2)

    cash = db.execute("SELECT cash FROM users WHERE id = :id", id = session["user_id"])[0]['cash']
    return render_template("index.html", portfolio = portfolio, cash = round(cash,2), sum = round(sum,2))
    """Show portfolio of stocks"""
    return apology("TODO")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "GET":
        return render_template("buy.html")
    else:
        num = int(request.form.get("num"))
        stock = request.form.get("stock")
        price = lookup(stock)

        # Check if the stock is valid
        if not price:
            return apology("Error invalid stock name")
        else:
            price = float(price['price'])

        cash = db.execute("SELECT cash FROM users WHERE id = :id", id = session["user_id"])

        # Check if the user has enough money
        cash = float(cash[0]['cash'])
        print(cash)
        if price*num > cash:
            return apology("Not enough money", 2)
        else:
            cash = cash-price*num
            db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash = cash, id = session["user_id"])
            update = db.execute("SELECT amount FROM portfolio WHERE id = :id AND stock = :stock", id = session["user_id"], stock = stock)
            print(update)
            # If there is no record of this stock in the portfolio,
            if not update:
                db.execute("INSERT INTO portfolio (id, stock, amount) VALUES (:id, :stock, :amount)", id = session["user_id"], stock = stock, amount = num)
            else:
                update = update[0]['amount']
                db.execute("UPDATE portfolio SET amount = :amount WHERE id = :id AND stock = :stock", amount = update + num, id = session["user_id"], stock = stock)
            db.execute("INSERT INTO history (id, type, stock, amount, price, date) VALUES (:id, 'B', :stock, :amount, :price, datetime())", id = session["user_id"], stock = stock, amount = num, price = price)
            return redirect("/")
    """Buy shares of stock"""
    return apology("TODO")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    hist = db.execute("SELECT * FROM history WHERE id = :id", id = session["user_id"])
    for row in hist:
        row['price'] = round(row['price'],2)

    return render_template("history.html", hist = hist)
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    else:
        # todo
        stock = request.form.get("stock")
        print("stock: " + stock)
        if not stock:
            return apology("Needs a stock name")
        else:
            price = lookup(stock)
            if not price:
                return apology("Invalid Stock Name")
            else:
                return render_template("quoteresult.html", name = price['name'], price = price['price'])
    return apology("Something Unexpected Happened With Quote")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        password_conf = request.form.get("password-conf")

        # Checking for username and password
        if not password == password_conf:
            return apology("Passwords were not the same", 403)
        if not username:
            return apology("Please provide a username",403)
        if not password:
            return apology("Please provide a password", 403)
        hash = generate_password_hash(password)
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=username, hash=hash)
        return redirect("/")
    return apology("Something unexpected happened")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():

    stocks = db.execute("SELECT stock FROM portfolio WHERE id = :id", id = session["user_id"])

    stocklist = []

    for row in stocks:
        stocklist.append(row['stock'])

    if request.method == "GET":
        return render_template("sell.html", stocklist = stocklist)
    else:
        stock = request.form.get("stock")
        amount = int(request.form.get("amount"))

        cash = db.execute("SELECT cash FROM users WHERE id = :id", id = session["user_id"])[0]['cash']

        current_amount = db.execute("SELECT amount FROM portfolio WHERE id = :id AND stock = :stock", id = session["user_id"], stock = stock)

        current_amount = int(current_amount[0]['amount'])

        if current_amount < amount:
            return apology("Error tried to sell more than what was had")
        elif amount <= 0:
            return apology("Error, requires a positive integer")
        else:
            amount = current_amount - amount
            cost = amount * float(lookup(stock)['price'])
            if amount == 0:
                db.execute("DELETE FROM portfolio WHERE id = :id AND stock = :stock", id = session["user_id"], stock = stock)
            else:
                db.execute("UPDATE portfolio SET amount = :amount WHERE id = :id and stock = :stock", amount = amount, id = session["user_id"], stock = stock)
            db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash = cash + cost, id = session["user_id"])
            db.execute("INSERT INTO history (id, type, stock, amount, price, date) VALUES (:id, 'S', :stock, :amount, :price, datetime())", id = session["user_id"], stock = stock, amount = amount, price = cost)
            return redirect("/")


    """Sell shares of stock"""
    return apology("TODO")


@app.route("/password", methods = ["GET", "POST"])
@login_required
def password():
    if request.method == "GET":
        return render_template("password.html")
    else:
        password = request.form.get("password")
        new_password = request.form.get("npassword")

        if not check_password_hash(db.execute("SELECT hash FROM users WHERE id = :id", id = session["user_id"])[0]['hash'],password):
            return apology("Incorrect password")
        else:
            hash = generate_password_hash(new_password)
            db.execute("UPDATE users SET hash = :hash WHERE id = :id", hash = hash, id = session["user_id"])
        return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
