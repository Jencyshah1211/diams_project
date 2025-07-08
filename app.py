from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
from datetime import datetime, date
import mysql.connector
import logging
import pandas as pd

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Change to a secure key in production
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

# MySQL configuration
MYSQL_USER = os.getenv("DB_USER")
MYSQL_PASSWORD = os.getenv("DB_PASSWORD")
MYSQL_HOST = os.getenv("DB_HOST")
MYSQL_DB = os.getenv("DB_NAME")

if not all([MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DB]):
    print("One or more database environment variables are missing")
    raise ValueError("Database configuration is incomplete")

mysql_config = {
    "user": MYSQL_USER,
    "password": MYSQL_PASSWORD,
    "host": MYSQL_HOST,
    "database": MYSQL_DB,
}
# print("mysql", mysql_config)
# File upload configuration
UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "xlsx", "xls"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def role_required(*roles, allow_guest=False):
    def decorator(f):
        from functools import wraps

        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_type = session.get("user_type", "guest")
            if user_type == "guest" and not allow_guest:
                flash(f"Please log in to view your {f.__name__}", "error")
                return redirect(url_for("login"))
            if user_type != "guest" and user_type not in roles:
                flash("Access denied: Unauthorized role", "error")
                return redirect(url_for("home"))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


@app.route("/")
def home():
    user_type = session.get("user_type", "guest")
    name = session.get("name", "")
    return render_template("index.html", user_type=user_type, name=name)


@app.route("/diamonds")
def diamonds():
    return render_template("diamonds.html")


@app.route("/diamonds/filter=")
def filter_diamonds():
    flash("Diamond filtering not implemented yet.", "info")
    return render_template("diamonds.html")


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
@role_required("buyer", allow_guest=True)
def cart():
    user_type = session.get("user_type", "guest")
    items = []
    return render_template("cart.html", user_type=user_type, items=items)


@app.route("/wishlist")
@role_required("buyer", allow_guest=True)
def wishlist():
    user_type = session.get("user_type", "guest")
    items = []
    return render_template("wishlist.html", user_type=user_type, items=items)


@app.route("/franchise")
def franchise():
    return render_template("franchise.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/profile")
def profile():
    user_email = session.get("user")
    if not user_email:
        flash("Please log in to view your profile", "error")
        return render_template("profile.html", logged_in=False)
    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (user_email,))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            conn.close()
            flash("User not found", "error")
            return render_template("profile.html", logged_in=False)
        profile_data = None
        if user["user_type"] == "buyer":
            cursor.execute("SELECT * FROM buyers WHERE user_id = %s", (user["id"],))
            profile_data = cursor.fetchone()
        elif user["user_type"] == "jeweller":
            cursor.execute("SELECT * FROM dealers WHERE user_id = %s", (user["id"],))
            profile_data = cursor.fetchone()
        else:  # supplier
            cursor.execute("SELECT * FROM suppliers WHERE user_id = %s", (user["id"],))
            profile_data = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template(
            "profile.html", logged_in=True, user=user, profile_data=profile_data
        )
    except Exception as e:
        logging.error(f"Error fetching profile: {e}")
        flash("An error occurred while loading profile", "error")
        return render_template("profile.html", logged_in=False)


@app.route("/profile/update", methods=["POST"])
def profile_update():
    user_email = session.get("user")
    if not user_email:
        flash("Please log in to update your profile", "error")
        return redirect(url_for("login"))
    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (user_email,))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            conn.close()
            flash("User not found", "error")
            return redirect(url_for("profile"))
        form = request.form
        if user["user_type"] == "buyer":
            cursor.execute(
                """
                UPDATE buyers
                SET first_name = %s, last_name = %s, address = %s, city = %s, state = %s, country = %s, pincode = %s
                WHERE user_id = %s
                """,
                (
                    form.get("first_name"),
                    form.get("last_name"),
                    form.get("address"),
                    form.get("city"),
                    form.get("state"),
                    form.get("country"),
                    form.get("pincode"),
                    user["id"],
                ),
            )
            cursor.execute(
                "UPDATE users SET email = %s, mobile_number = %s WHERE id = %s",
                (form.get("email"), form.get("mobile_number"), user["id"]),
            )
        elif user["user_type"] == "jeweller":
            cursor.execute(
                """
                UPDATE dealers
                SET company_name = %s, first_name = %s, last_name = %s, company_email = %s, company_mobile = %s,
                    address1 = %s, dealer_city = %s, dealer_state = %s, dealer_country = %s, pincode = %s
                WHERE user_id = %s
                """,
                (
                    form.get("company_name"),
                    form.get("first_name"),
                    form.get("last_name"),
                    form.get("company_email"),
                    form.get("company_mobile"),
                    form.get("address1"),
                    form.get("city"),
                    form.get("state"),
                    form.get("country"),
                    form.get("pincode"),
                    user["id"],
                ),
            )
        else:  # supplier
            cursor.execute(
                """
                UPDATE suppliers
                SET company_name = %s, supervisor_name = %s, supervisor_email = %s, supervisor_mobile = %s,
                    address1 = %s, city = %s, state = %s, country = %s, pincode = %s
                WHERE user_id = %s
                """,
                (
                    form.get("company_name"),
                    form.get("supervisor_name"),
                    form.get("supervisor_email"),
                    form.get("supervisor_mobile"),
                    form.get("address1"),
                    form.get("city"),
                    form.get("state"),
                    form.get("country"),
                    form.get("pincode"),
                    user["id"],
                ),
            )
        conn.commit()
        cursor.close()
        conn.close()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))
    except Exception as e:
        logging.error(f"Error updating profile: {e}")
        flash("An error occurred while updating profile", "error")
        return redirect(url_for("profile"))


@app.route("/calculator")
@role_required("jeweller")
def calculator():
    return render_template("calculator.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        logging.debug(f"Login attempt: email={email}, password={'*' * len(password)}")
        if not email or not password:
            logging.error("Missing email or password in login form")
            flash("Please provide both email and password", "error")
            return render_template("profile.html", logged_in=False)
        try:
            conn = mysql.connector.connect(**mysql_config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            if not user:
                logging.error(f"No user found for email: {email}")
                flash("Invalid email or password", "error")
                cursor.close()
                conn.close()
                return render_template("profile.html", logged_in=False)
            name = None
            if user["user_type"] == "buyer":
                cursor.execute(
                    "SELECT first_name FROM buyers WHERE user_id = %s", (user["id"],)
                )
                result = cursor.fetchone()
                name = result["first_name"] if result else None
            elif user["user_type"] == "jeweller":
                cursor.execute(
                    "SELECT first_name FROM dealers WHERE user_id = %s", (user["id"],)
                )
                result = cursor.fetchone()
                name = result["first_name"] if result else None
            else:  # supplier
                cursor.execute(
                    "SELECT company_name FROM suppliers WHERE user_id = %s",
                    (user["id"],),
                )
                result = cursor.fetchone()
                name = result["company_name"] if result else None
            if not name:
                logging.error(
                    f"No name found for user_id: {user['id']}, user_type: {user['user_type']}"
                )
                flash("Error retrieving user information", "error")
                cursor.close()
                conn.close()
                return render_template("profile.html", logged_in=False)
            if check_password_hash(user["password_hash"], password):
                session["user"] = email
                session["name"] = name
                session["user_type"] = user["user_type"]
                session["user_id"] = user["id"]
                logging.info(f"User logged in successfully: {email}")
                flash("Logged in successfully!", "success")
                cursor.close()
                conn.close()
                return redirect(url_for("home"))
            else:
                logging.error(f"Invalid password for email: {email}")
                flash("Invalid email or password", "error")
                cursor.close()
                conn.close()
                return render_template("profile.html", logged_in=False)
        except Exception as e:
            logging.error(f"Error during login: {e}")
            flash("An error occurred during login", "error")
            cursor.close()
            conn.close()
            return render_template("profile.html", logged_in=False)
    return render_template("profile.html", logged_in=False)


@app.route("/signup/<user_type>", methods=["GET", "POST"])
def signup(user_type):
    user_type_map = {
        "guest": "buyer",
        "jeweller": "jeweller",
        "supplier": "supplier",
    }
    selected_user_type = user_type_map.get(user_type)
    if not selected_user_type:
        flash("Invalid user type", "error")
        return redirect(url_for("home"))
    if request.method == "POST":
        form = request.form
        logging.debug(f"Form data received: {dict(form)}")
        email = (
            form.get("email")
            if selected_user_type == "buyer"
            else form.get("login_email")
        )
        password = form.get("password")
        confirm_password = form.get("confirm_password")
        agree = form.get("agree")
        required_fields = {
            "buyer": [
                "email",
                "first_name",
                "last_name",
                "mobile_number",
                "country_code",
                "country",
                "state",
                "city",
                "address",
                "password",
                "confirm_password",
                "agree",
            ],
            "jeweller": [
                "login_email",
                "login_mobile",
                "login_country_code",
                "company_name",
                "company_email",
                "company_mobile",
                "company_country_code",
                "dealer_country",
                "dealer_state",
                "dealer_city",
                "address1",
                "company_type",
                "license_number",
                "first_name",
                "last_name",
                "password",
                "confirm_password",
                "agree",
            ],
            "supplier": [
                "login_email",
                "login_mobile",
                "login_country_code",
                "company_name",
                "inventory_type",
                "country",
                "state",
                "city",
                "address1",
                "company_type",
                "business_license_number",
                "supervisor_name",
                "supervisor_email",
                "supervisor_mobile",
                "supervisor_country_code",
                "password",
                "confirm_password",
                "agree",
            ],
        }
        for field in required_fields[selected_user_type]:
            if field not in ["license_document", "business_license_document"]:
                if not form.get(field):
                    logging.error(f"Missing required field: {field}")
                    flash(
                        f"Missing required field: {field.replace('_', ' ').title()}",
                        "error",
                    )
                    return render_template("signup.html", user_type=selected_user_type)
        if not agree:
            logging.error("Terms and conditions not agreed")
            flash("You must agree to the Terms & Conditions", "error")
            return render_template("signup.html", user_type=selected_user_type)
        if password != confirm_password:
            logging.error("Passwords do not match")
            flash("Passwords do not match", "error")
            return render_template("signup.html", user_type=selected_user_type)
        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(**mysql_config)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                logging.info(f"User already exists: {email}")
                flash("User already exists, please login", "error")
                cursor.close()
                conn.close()
                return redirect(url_for("login"))
            name = (
                form.get("first_name")
                if selected_user_type in ["buyer", "jeweller"]
                else form.get("company_name")
            )
            cursor.execute(
                """
                INSERT INTO users (email, password_hash, user_type, mobile_number, country_code, is_active, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    email,
                    generate_password_hash(password),
                    selected_user_type,
                    (
                        form.get("mobile_number")
                        if selected_user_type == "buyer"
                        else form.get("login_mobile")
                    ),
                    (
                        form.get("country_code")
                        if selected_user_type == "buyer"
                        else form.get("login_country_code")
                    ),
                    True,
                    datetime.now(),
                ),
            )
            user_id = cursor.lastrowid
            if selected_user_type == "buyer":
                cursor.execute(
                    """
                    INSERT INTO buyers (user_id, first_name, last_name, address, country, state, city, pincode)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        form.get("first_name"),
                        form.get("last_name"),
                        form.get("address"),
                        form.get("country"),
                        form.get("state"),
                        form.get("city"),
                        form.get("pincode"),
                    ),
                )
            elif selected_user_type == "jeweller":
                if (
                    "license_document" not in request.files
                    or not request.files["license_document"].filename
                ):
                    logging.error("Missing license document")
                    flash("Please upload a business license document", "error")
                    return render_template("signup.html", user_type=selected_user_type)
                license_document = request.files["license_document"]
                if not allowed_file(license_document.filename):
                    logging.error("Invalid license document format")
                    flash(
                        "Please upload a valid business license document (PDF, PNG, JPG, JPEG)",
                        "error",
                    )
                    return render_template("signup.html", user_type=selected_user_type)
                filename = secure_filename(license_document.filename)
                license_document_path = os.path.join(
                    app.config["UPLOAD_FOLDER"], filename
                )
                license_document.save(license_document_path)
                iec_document = request.files.get("iec_document")
                iec_document_path = None
                if (
                    iec_document
                    and iec_document.filename
                    and allowed_file(iec_document.filename)
                ):
                    filename = secure_filename(iec_document.filename)
                    iec_document_path = os.path.join(
                        app.config["UPLOAD_FOLDER"], filename
                    )
                    iec_document.save(iec_document_path)
                passport_front = request.files.get("passport_front")
                passport_front_path = None
                if (
                    passport_front
                    and passport_front.filename
                    and allowed_file(passport_front.filename)
                ):
                    filename = secure_filename(passport_front.filename)
                    passport_front_path = os.path.join(
                        app.config["UPLOAD_FOLDER"], filename
                    )
                    passport_front.save(passport_front_path)
                passport_back = request.files.get("passport_back")
                passport_back_path = None
                if (
                    passport_back
                    and passport_back.filename
                    and allowed_file(passport_back.filename)
                ):
                    filename = secure_filename(passport_back.filename)
                    passport_back_path = os.path.join(
                        app.config["UPLOAD_FOLDER"], filename
                    )
                    passport_back.save(passport_back_path)
                driving_license = request.files.get("driving_license")
                driving_license_path = None
                if (
                    driving_license
                    and driving_license.filename
                    and allowed_file(driving_license.filename)
                ):
                    filename = secure_filename(driving_license.filename)
                    driving_license_path = os.path.join(
                        app.config["UPLOAD_FOLDER"], filename
                    )
                    driving_license.save(driving_license_path)
                dob = None
                if form.get("dob"):
                    try:
                        dob = datetime.strptime(form.get("dob"), "%Y-%m-%d").date()
                    except ValueError:
                        logging.error("Invalid date of birth format")
                        flash("Invalid date of birth format. Use YYYY-MM-DD.", "error")
                        return render_template(
                            "signup.html", user_type=selected_user_type
                        )
                cursor.execute(
                    """
                    INSERT INTO dealers (
                        user_id, company_name, company_email, company_mobile, company_country_code,
                        address1, address2, country, state, city, pincode, company_type,
                        nature_of_business, license_number, license_document, iec, iec_document,
                        first_name, last_name, passport_number, passport_front, passport_back,
                        dob, driving_license_number, driving_license, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        form.get("company_name"),
                        form.get("company_email"),
                        form.get("company_mobile"),
                        form.get("company_country_code"),
                        form.get("address1"),
                        form.get("address2"),
                        form.get("dealer_country"),
                        form.get("dealer_state"),
                        form.get("dealer_city"),
                        form.get("pincode"),
                        form.get("company_type"),
                        form.get("nature_of_business"),
                        form.get("license_number"),
                        license_document_path,
                        form.get("iec"),
                        iec_document_path,
                        form.get("first_name"),
                        form.get("last_name"),
                        form.get("passport_number"),
                        passport_front_path,
                        passport_back_path,
                        dob,
                        form.get("driving_license_number"),
                        driving_license_path,
                        datetime.now(),
                    ),
                )
            elif selected_user_type == "supplier":
                if (
                    "business_license_document" not in request.files
                    or not request.files["business_license_document"].filename
                ):
                    logging.error("Missing business license document")
                    flash("Please upload a business license document", "error")
                    return render_template("signup.html", user_type=selected_user_type)
                business_license_document = request.files["business_license_document"]
                if not allowed_file(business_license_document.filename):
                    logging.error("Invalid business license document format")
                    flash(
                        "Please upload a valid business license document (PDF, PNG, JPG, JPEG)",
                        "error",
                    )
                    return render_template("signup.html", user_type=selected_user_type)
                filename = secure_filename(business_license_document.filename)
                business_license_document_path = os.path.join(
                    app.config["UPLOAD_FOLDER"], filename
                )
                business_license_document.save(business_license_document_path)
                iec_documents = request.files.get("iec_documents")
                iec_documents_path = None
                if (
                    iec_documents
                    and iec_documents.filename
                    and allowed_file(iec_documents.filename)
                ):
                    filename = secure_filename(iec_documents.filename)
                    iec_documents_path = os.path.join(
                        app.config["UPLOAD_FOLDER"], filename
                    )
                    iec_documents.save(iec_documents_path)
                cursor.execute(
                    """
                    INSERT INTO suppliers (
                        user_id, company_name, inventory_type, address1, address2, country, state, city,
                        pincode, company_type, nature_of_business, business_license_number,
                        business_license_document, iec, iec_documents, bank_name, branch_name,
                        bank_account_number, account_type, ifsc_code, swift_code, supervisor_name,
                        supervisor_email, supervisor_mobile, supervisor_country_code, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        form.get("company_name"),
                        form.get("inventory_type"),
                        form.get("address1"),
                        form.get("address2"),
                        form.get("country"),
                        form.get("state"),
                        form.get("city"),
                        form.get("pincode"),
                        form.get("company_type"),
                        form.get("nature_of_business"),
                        form.get("business_license_number"),
                        business_license_document_path,
                        form.get("iec"),
                        iec_documents_path,
                        form.get("bank_name"),
                        form.get("branch_name"),
                        form.get("bank_account_number"),
                        form.get("account_type"),
                        form.get("ifsc_code"),
                        form.get("swift_code"),
                        form.get("supervisor_name"),
                        form.get("supervisor_email"),
                        form.get("supervisor_mobile"),
                        form.get("supervisor_country_code"),
                        datetime.now(),
                    ),
                )
            conn.commit()
            logging.info(f"User signed up successfully: {email}")
            session["user"] = email
            session["name"] = name
            session["user_type"] = selected_user_type
            session["user_id"] = user_id
            flash("Signup successful!", "success")
            return redirect(url_for("home"))
        except Exception as e:
            logging.error(f"Error during signup: {e}")
            flash("An error occurred during signup", "error")
            return render_template("signup.html", user_type=selected_user_type)
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    return render_template("signup.html", user_type=selected_user_type)


@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("name", None)
    session.pop("user_type", None)
    session.pop("user_id", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))


@app.route("/supplier_hub")
@role_required("supplier")
def supplier_hub():
    return render_template("supplier_hub.html")


@app.route("/api/supplier/inventory/upload", methods=["POST"])
@role_required("supplier")
def upload_inventory():
    try:
        if "inventory_file" not in request.files:
            flash("No file uploaded", "error")
            return redirect(url_for("supplier_hub"))
        file = request.files["inventory_file"]
        if not file or not allowed_file(file.filename):
            flash(
                "Invalid file format. Please upload an Excel file (.xlsx, .xls)",
                "error",
            )
            return redirect(url_for("supplier_hub"))
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)
        df = pd.read_excel(file_path)
        logging.info(f"Uploaded Excel file contents: {df.to_dict(orient='records')}")
        flash(
            "Inventory file uploaded successfully! Awaiting diamonds table for processing.",
            "success",
        )
        return redirect(url_for("supplier_hub"))
    except Exception as e:
        logging.error(f"Error uploading inventory: {e}")
        flash(f"Error uploading inventory: {str(e)}", "error")
        return redirect(url_for("supplier_hub"))


@app.route("/api/supplier/inventory")
@role_required("supplier")
def get_supplier_inventory():
    return jsonify([])


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5001)
