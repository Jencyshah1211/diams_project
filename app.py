from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Change to a secure key in production

# Dummy users for demo (replace with DB later)
users = {
    "john@example.com": {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "phone": "+1 555-123-4567",
        "street_address": "123 Main Street",
        "city": "New York",
        "state": "NY",
        "zip": "10001",
        "country": "USA",
        "password_hash": generate_password_hash("password123"),
    }
}


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/diamonds")
def diamonds():
    return render_template("diamonds.html")


@app.route("/diamonds/filter=")
def filter_diamonds():
    shape = request.args.get("shape")
    quality = request.args.get("quality")
    price_min = request.args.get("price_min", 0)
    price_max = request.args.get("price_max", 9999999)

    # Build query dynamically
    query = Diamond.query
    if shape:
        query = query.filter_by(shape=shape)
    if quality:
        query = query.filter_by(quality=quality)
    query = query.filter(Diamond.price.between(price_min, price_max))

    diamonds = query.all()
    return render_template("diamonds.html", diamonds=diamonds)


@app.route("/jewelry")
def jewelry():
    return render_template("jewelry.html")


@app.route("/education")
@app.route("/education/<section>")
def education(section="5cs"):
    return render_template("education.html", section=section)


@app.route("/education/section/<section_name>")
def load_section_partial(section_name):
    try:
        return render_template(f"education/{section_name}.html")
    except:
        return "Content not found", 404


@app.route("/cart")
def cart():
    return render_template("cart.html")


@app.route("/franchise")
def franchise():
    return render_template("franchise.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/profile")
def profile():
    user_email = session.get("user")
    if not user_email or user_email not in users:
        # User not logged in or unknown
        return render_template("profile.html", logged_in=False)

    user = users[user_email]
    return render_template("profile.html", logged_in=True, user=user)


# Dummy login route for demo
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = users.get(email)
        if email and password:
            session["user"] = email
            flash("Logged in successfully!", "success")
            user = {
                "john.doe@example.com": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john.doe@example.com",
                    "phone": "+1 (555) 123-4567",
                    "avatar": "/static/john-avatar.png",
                    "address": "123 Main Street",
                    "city": "New York",
                    "state": "NY",
                    "zipcode": "10001",
                    "country": "United States",
                }
            }

            return render_template("profile.html", logged_in=True, user=user)
        else:
            flash("Invalid email or password", "error")
    return render_template("profile.html", logged_in=False)


@app.route("/signup/<user_type>", methods=["GET", "POST"])
def signup(user_type):
    # Map URL user_type to internal user type
    user_type_map = {
        "guest": "buyer",  # guest maps to buyer
        "jeweller": "jeweller",  # jeweller maps to jeweller
        "supplier": "supplier",  # supplier maps to supplier
    }

    selected_user_type = user_type_map.get(user_type, None)

    if request.method == "POST":
        # Handle form submission
        ...

    return render_template("signup.html", user_type=selected_user_type)


# Dummy logout route
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5001)
