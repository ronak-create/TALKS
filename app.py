from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    send_from_directory
)
from markupsafe import Markup
import os
import random
import re
from flask_mail import Mail, Message
from functools import wraps
import sqlite3
from datetime import timedelta, datetime
import secrets
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from werkzeug.security import generate_password_hash, check_password_hash


# Configuration
DATABASE = "talks.db"  # Path to your SQLite database file

app = Flask(__name__)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
app.secret_key = "djfby7r67834en"

mail = Mail(app)


# Database connection function for SQLite
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Enable dictionary-like row access
    return conn


# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


# Function to calculate time ago
def time_ago(created_at):
    if isinstance(created_at, str):  # Check if it's a string
        created_at = datetime.fromisoformat(created_at)  # Convert string to datetime
    now = datetime.utcnow()
    diff = now - created_at

    seconds = diff.total_seconds()
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m"
    elif seconds < 86400:
        return f"{int(seconds // 3600)}h"
    elif seconds < 604800:
        return f"{int(seconds // 86400)}d"
    elif seconds < 2419200:
        return f"{int(seconds // 604800)}w"
    elif seconds < 31536000:
        return f"{int(seconds // 2419200)}mo"
    else:
        return f"{int(seconds // 31536000)}y"
    
@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'site-map.xml')

# @app.route('/calculate_post_cost/<int:post_id>', methods=['GET'])
def calculate_post_cost(post_like_count, post_comment_count):
    base_cost = 10  # Minimum cost for any post
    multiplier = 5  # Adjust for your app's economy

    post_popularity_score = (post_like_count * 0.5) + (post_comment_count * 0.3)
    post_cost_in_perks = base_cost + (post_popularity_score * multiplier)
    return int(post_cost_in_perks)

# Home route to handle posts and comments
@app.route("/home")
@login_required
def home():
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = session.get("user_id")  # Get user_id from session

    cursor.execute(
        """
        SELECT posts.id AS post_id, posts.content, posts.created_at, users.username AS post_user,
            COUNT(DISTINCT post_likes.id) AS like_count, 
            COUNT(DISTINCT comments.id) AS comment_count,
            comments.id AS comment_id, comments.content AS comment_content, 
            comment_users.username AS comment_user,
            COUNT(DISTINCT comment_likes.id) AS comment_like_count
        FROM posts
        JOIN users ON posts.user_id = users.id
        LEFT JOIN post_likes ON post_likes.post_id = posts.id
        LEFT JOIN comments ON comments.post_id = posts.id
        LEFT JOIN users AS comment_users ON comments.user_id = comment_users.id
        LEFT JOIN comment_likes ON comment_likes.comment_id = comments.id
        GROUP BY posts.id, comments.id
        ORDER BY posts.created_at DESC, comments.created_at ASC
        """
    )
    posts = cursor.fetchall()

    grouped_posts = {}
    for post in posts:
        post_id = post["post_id"]
        content_with_links = re.sub(
            r"(#\w+)",
            lambda match: f'<a href="hashtags/{match.group(1)[1:]}" class="hashtag-links">{match.group(1)}</a>',
            post["content"],
        )
        content_with_links = Markup(content_with_links)
        if post_id not in grouped_posts:
            grouped_posts[post_id] = {
                "post_id": post_id,
                "post_content_raw": post["content"],
                "post_content": content_with_links,
                "created_at": time_ago(post["created_at"]),
                "username": post["post_user"],
                "post_cost":calculate_post_cost(post["like_count"], post["comment_count"]),
                "like_count": post["like_count"],
                "comments": [],
                "is_liked": False,
            }

        if user_id:
            cursor.execute(
                "SELECT * FROM post_likes WHERE post_id = ? AND user_id = ?",
                (post_id, user_id),
            )
            if cursor.fetchone():
                grouped_posts[post_id]["is_liked"] = True

        if post["comment_id"]:
            comment_data = {
                "comment_id": post["comment_id"],
                "username": post["comment_user"],
                "content": post["comment_content"],
                "like_count": post["comment_like_count"],
                "is_liked": False,
            }

            if user_id:
                cursor.execute(
                    "SELECT * FROM comment_likes WHERE comment_id = ? AND user_id = ?",
                    (post["comment_id"], user_id),
                )
                if cursor.fetchone():
                    comment_data["is_liked"] = True

            grouped_posts[post_id]["comments"].append(comment_data)

    final_posts = list(grouped_posts.values())

    conn.close()

    return render_template("index.html", posts=final_posts)



# @app.route('/buy_post/<int:post_id>', methods=['POST'])
# def buy_post(post_id):
#     user = User.query.get(session['user_id'])
#     post = Post.query.get(post_id)

#     if user.perks >= post.cost_in_perks:
#         user.perks -= post.cost_in_perks
#         user.purchased_posts.append(post)  # Assuming a many-to-many relationship
#         db.session.commit()
#         return jsonify({'message': 'Post purchased successfully!'})
#     else:
#         return jsonify({'error': 'Not enough perks to buy this post.'}), 400




@app.route("/search", methods=["GET"])
@login_required
def search():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, bio FROM users ORDER BY username ASC")  # Adjust table name if needed
    users = cursor.fetchall()

    # Format data as a list of dictionaries for JSON output
    users = [
        {"id": user[0], "username": user[1], "bio": user[2]}
        for user in users
    ]
    return render_template("search.html", users=users)


def send_welcome_email(user_email, user_name):
    sender_email = "talks.member@gmail.com"  # Your email address
    sender_password = (
        "vzim fodm ogkx ewfd"  # Your email password (or app password if using Gmail)
    )
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    verification_code = str(random.randint(100000, 999999))

    # HTML email content (template with branding, colors, and features)
    html_content = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f4f4f9;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: auto;
                background-color: #ffffff;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 0 15px rgba(0, 0, 0, 0.1);
            }}
            h1 {{
                color: #2d3748;
                text-align: center;
            }}
            h2 {{
                color: #4A90E2;
                font-size: 24px;
                text-align: center;
            }}
            p {{
                font-size: 16px;
                color: #333333;
                line-height: 1.6;
                text-align: center;
            }}
            .features {{
                display: flex;
                justify-content: space-around;
                margin-top: 20px;
                margin-bottom: 20px;
            }}
            .feature-card {{
                background-color: #fafafa;
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                width: 30%;
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            }}
            .feature-card img {{
                width: 100px;
                height: 100px;
                object-fit: contain;
                margin-bottom: 10px;
            }}
            .cta-button {{
                display: block;
                background-color: #4A90E2;
                color: white;
                padding: 15px;
                width: 100%;
                text-align: center;
                font-size: 18px;
                border-radius: 5px;
                text-decoration: none;
                margin-top: 20px;
            }}
            .footer {{
                text-align: center;
                font-size: 12px;
                color: #999999;
                margin-top: 40px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Welcome to Our Platform, {user_name}!</h1>
            <p>We're thrilled to have you join us! As part of our community, you now have access to all the amazing features that can help you connect, share, and grow.</p>
            <p>Your verification code is: <strong>{verification_code}</strong></p>
            <p>Please enter this code to verify your email.</p>
            <div class="features">
                <div class="feature-card">
                    <h2>Build Connections That Matter</h2>
                    <p>Join a thriving community where ideas, stories, and perspectives come alive.</p>
                </div>
                <div class="feature-card">
                    <h2>Express Yourself Freely</h2>
                    <p>Your unique voice deserves to be heard-share, engage, and inspire.</p>
                </div>
                <div class="feature-card">
                    <h2>A Platform Made for You</h2>
                    <p>Designed for meaningful interactions, authentic expression, and real connections.</p>
                </div>
            </div>
            
            <a href="https://talks.pythonanywhere.com" class="cta-button">Explore Features</a>
            
            <div class="footer">
                <p>If you have any questions or need help, feel free to <a href="mailto:talks.member@gmail.com">contact us</a>.</p>
                <p>Best regards,<br>The TALKS Team</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Set up the MIME message
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = user_email
    msg["Subject"] = "Welcome to TALKS!"
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        # Connect to the SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Start TLS encryption

        # Log in to the server
        server.login(sender_email, sender_password)

        # Send the email
        server.sendmail(sender_email, user_email, msg.as_string())
    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Close the SMTP server connection
        server.quit()
    return verification_code


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        phone = request.form["contact_number"]
        email = request.form["email"]
        country_code = request.form["country_code"]
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        phone = f"{country_code}{phone}"

        # Generate verification code
        verification_code = send_welcome_email(email, username)

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if email already exists
        cursor.execute(
            "SELECT COUNT(1) FROM email_verifications WHERE email = ?", (email,)
        )
        existing_user = cursor.fetchone()[0]

        if existing_user:
            flash("This email is already registered. Please use a different email.")
            return redirect(url_for("register"))

        session["username"] = username
        session["password"] = password
        session["phone"] = phone
        session["email"] = email

        # Insert the verification code into the email_verifications table
        cursor.execute(
            "INSERT INTO email_verifications (email, code) VALUES (?, ?)",
            (email, verification_code),
        )
        conn.commit()

        # Send verification emai

        flash(
            "A verification email has been sent to your email address. Please verify it."
        )
        return redirect(url_for("verify_email", email=email))

    return render_template("register.html")


@app.route("/verify_email/<email>", methods=["GET", "POST"])
def verify_email(email):
    if request.method == "POST":
        entered_code = request.form["verification_code"]
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the code entered by the user matches the one stored in the database
        cursor.execute(
            "SELECT * FROM email_verifications WHERE email = ? AND code = ?",
            (email, entered_code),
        )
        verification = cursor.fetchone()
        if verification:
            # Retrieve the user data from session
            username = session.get("username")
            password = session.get("password")
            country_code = session.get("country_code")
            phone = session.get("phone")

            # Proceed with user registration
            cursor.execute(
                "INSERT INTO users (username, password, email, contact) VALUES (?, ?, ?, ?)",
                (
                    username,
                    generate_password_hash(password, method="pbkdf2:sha256"),
                    email,
                    f"{country_code}{phone}",
                ),
            )
            conn.commit()

            # Remove the verification code from the database as it’s already used
            cursor.execute("DELETE FROM email_verifications WHERE email = ?", (email,))
            conn.commit()

            # Clear the session
            session.clear()

            flash("Email verified successfully! You are now registered.")
            return redirect(url_for("login"))
        else:
            flash("Invalid verification code. Please try again.")
            return redirect(url_for("verify_email", email=email))

    return render_template("verify_email.html", email=email)


@app.route("/resend_verification/<email>", methods=["GET"])
def resend_verification(email):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Generate a new verification code
    new_code = send_welcome_email(email, session.get("username", "User"))
    cursor.execute(
        "UPDATE email_verifications SET code = ? WHERE email = ?", (new_code, email)
    )
    conn.commit()

    flash("A new verification code has been sent to your email.")
    return redirect(url_for("verify_email", email=email))


@app.route("/")
def landing():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    return render_template("landing.html", user_count=user_count)


@app.route("/send_message", methods=["POST"])
def send_message():
    if request.method == "POST":
        # Get form data
        name = request.form["name"]
        email = request.form["email"]
        message = request.form["message"]

        # Save data to SQLite
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_queries (name, email, message) 
            VALUES (?, ?, ?)
        """,
            (name, email, message),
        )
        conn.commit()
        conn.close()

        # Flash success message
        flash("Your message has been sent successfully!", "success")

        return redirect("/#contact")

    return render_template("landing.html")  # Redirect back to contact form


@app.route("/check_session")
def check_session():
    if "user_id" in session:
        # User is logged in
        return jsonify({"is_logged_in": True})
    else:
        # User is not logged in
        return jsonify({"is_logged_in": False})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?", (username, username)
        )
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session.permanent = True
            flash("Login successful!")
            return redirect(url_for("home"))
        else:
            return render_template("login.html", message="Invalid username or password!")

    return render_template("login.html")



@app.route("/create_post", methods=["GET", "POST"])
@login_required
def create_post():
    if request.method == "POST":
        content = request.form["content"]
        user_id = session["user_id"]

        hashtags = extract_hashtags(content)

        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert the post into the posts table
        cursor.execute(
            "INSERT INTO posts (user_id, content) VALUES (?, ?)", (user_id, content)
        )
        conn.commit()

        # Get the post_id of the newly inserted post
        post_id = cursor.lastrowid

        # Insert or update hashtags in the hashtags table
        for tag in hashtags:
            cursor.execute("SELECT * FROM hashtags WHERE tag = ?", (tag,))
            hashtag_row = cursor.fetchone()

            if hashtag_row:
                # If hashtag exists, append the post_id to the post_ids column
                new_post_ids = (
                    f"{hashtag_row['post_ids']},{post_id}"
                    if hashtag_row["post_ids"]
                    else str(post_id)
                )
                cursor.execute(
                    "UPDATE hashtags SET count = count + 1, post_ids = ? WHERE tag = ?",
                    (new_post_ids, tag),
                )
            else:
                # If hashtag doesn't exist, insert it into the hashtags table with the post_id
                cursor.execute(
                    "INSERT INTO hashtags (tag, count, post_ids) VALUES (?, 1, ?)",
                    (tag, str(post_id)),
                )

        conn.commit()
        conn.close()

        flash("Post created successfully!")
        return redirect(url_for("home"))

    return render_template("create_post.html")




# Function to extract hashtags from the content
def extract_hashtags(content):
    return re.findall(r"#\w+", content)


@app.route("/comment/<int:post_id>", methods=["POST"])
def comment(post_id):
    if "user_id" not in session:
        flash("Please log in to comment.")
        return redirect(url_for("login"))

    content = request.form["content"]
    user_id = session["user_id"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)",
        (post_id, user_id, content),
    )
    conn.commit()
    conn.close()

    flash("Comment added!")
    return redirect(url_for("home"))


@app.route("/like_post/<int:post_id>", methods=["POST"])
def like_post(post_id):
    if "user_id" not in session:
        flash("Please log in to like posts.")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM post_likes WHERE post_id = ? AND user_id = ?", (post_id, user_id)
    )
    like = cursor.fetchone()

    if like:
        cursor.execute(
            "DELETE FROM post_likes WHERE post_id = ? AND user_id = ?",
            (post_id, user_id),
        )
        action = "unliked"
    else:
        cursor.execute(
            "INSERT INTO post_likes (post_id, user_id) VALUES (?, ?)",
            (post_id, user_id),
        )
        action = "liked"

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM post_likes WHERE post_id = ?", (post_id,))
    like_count = cursor.fetchone()[0]

    conn.close()

    return jsonify({"action": action, "like_count": like_count})


@app.route("/delete_post/<int:post_id>", methods=["POST", "GET"])
@login_required
def delete_post(post_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Delete the post
    cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()

    flash("Post deleted successfully!")
    return redirect(url_for("home"))


@app.route("/edit_post/<int:post_id>", methods=["POST"])
def edit_post(post_id):
    new_content = request.form.get("content")
    if not new_content:
        flash("Content cannot be empty.")
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE posts SET content = ? WHERE id = ?", (new_content, post_id))
    conn.commit()
    conn.close()

    flash("Post updated successfully.")
    return redirect(url_for("home"))


# Report post route
@app.route("/report_post/<int:post_id>", methods=["POST"])
def report_post(post_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reports (post_id, status) VALUES (?, 'Pending')", (post_id,)
    )
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Report submitted"})


@app.route("/like_comment/<int:comment_id>", methods=["POST"])
def like_comment(comment_id):
    if "user_id" not in session:
        flash("Please log in to like comments.")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM comment_likes WHERE comment_id = ? AND user_id = ?",
        (comment_id, user_id),
    )
    like = cursor.fetchone()

    if like:
        cursor.execute(
            "DELETE FROM comment_likes WHERE comment_id = ? AND user_id = ?",
            (comment_id, user_id),
        )
        action = "unliked"
    else:
        cursor.execute(
            "INSERT INTO comment_likes (comment_id, user_id) VALUES (?, ?)",
            (comment_id, user_id),
        )
        action = "liked"

    conn.commit()

    cursor.execute(
        "SELECT COUNT(*) FROM comment_likes WHERE comment_id = ?", (comment_id,)
    )
    like_count = cursor.fetchone()[0]

    conn.close()

    return jsonify({"action": action, "like_count": like_count})


@app.route("/settings")
@login_required
def settings():
    if "user_id" not in session:
        redirect(url_for("login"))
    user_id = session["user_id"]

    # Get the username from the database based on the user ID
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    # Pass the username to the template
    return render_template("settings.html", username=user["username"])


@app.route("/trending")
@login_required
def trending():
    return render_template("trending.html")


@app.route("/trending_hashtags")
@login_required
def trending_hashtags():
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch top 10 hashtags by count (in descending order)
    cursor.execute(
        """
        SELECT tag, count FROM hashtags
        ORDER BY count DESC
        LIMIT 10;
    """
    )
    trending_hashtags = cursor.fetchall()

    # Convert the result (Row objects) into a list of dictionaries for JSON serialization
    trending_hashtags_list = [
        {"tag": row[0], "count": row[1]} for row in trending_hashtags
    ]

    # Close the connection
    conn.close()

    # Return the trending hashtags as a JSON response
    return jsonify(trending_hashtags_list)


@app.route("/hashtags/<tag>")
def hashtags(tag):
    conn = get_db_connection()
    cursor = conn.cursor()
    tag = "#" + tag

    # Fetch the hashtag details
    cursor.execute("SELECT * FROM hashtags WHERE tag = ?", (tag,))
    hashtag = cursor.fetchone()

    if hashtag:
        # Fetch the post IDs associated with the hashtag
        post_ids = hashtag["post_ids"].split(",")

        # Fetch the posts associated with those post IDs
        posts = []
        for post_id in post_ids:
            cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
            post = cursor.fetchone()

            if post:
                # Convert the sqlite3.Row to a dictionary
                post_dict = dict(post)
                post_dict["post_id"] = post_dict.pop("id")
                content_with_links = re.sub(
                    r"(#\w+)",
                    lambda match: f'<a href="{url_for("hashtags", tag=match.group(1)[1:])}" class="hashtag-links">{match.group(1)}</a>',
                    post["content"],
                )
                content_with_links = Markup(content_with_links)
                post_dict["content"] = content_with_links

                # Fetch the user associated with this post using the user_id
                cursor.execute(
                    "SELECT * FROM users WHERE id = ?", (post_dict["user_id"],)
                )
                user = cursor.fetchone()

                # Add the user name to the post dictionary
                if user:
                    post_dict["user_name"] = user["username"]
                else:
                    post_dict["user_name"] = "Unknown User"  # In case no user is found

                posts.append(post_dict)

        conn.close()
        return render_template("hashtag_posts.html", tag=tag[1:], posts=posts)

    conn.close()
    flash("No posts found for this hashtag.")
    return redirect(url_for("home"))


@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    if "username" not in session:
        return redirect(url_for("login"))  # Redirect if user is not logged in

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch user details from the database using raw SQL
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()  # Get the first matching user

    # Fetch the user's posts with comments
    cursor.execute(
        """
        SELECT posts.id AS post_id, posts.content, posts.created_at, users.username AS post_user,
            COUNT(DISTINCT post_likes.id) AS like_count,
            COUNT(DISTINCT comments.id) AS comment_count,
            comments.id AS comment_id, comments.content AS comment_content, 
            comment_users.username AS comment_user,
            COUNT(DISTINCT comment_likes.id) AS comment_like_count
        FROM posts
        JOIN users ON posts.user_id = users.id
        LEFT JOIN post_likes ON post_likes.post_id = posts.id
        LEFT JOIN comments ON comments.post_id = posts.id
        LEFT JOIN users AS comment_users ON comments.user_id = comment_users.id
        LEFT JOIN comment_likes ON comment_likes.comment_id = comments.id
        WHERE posts.user_id = ?
        GROUP BY posts.id, comments.id
        ORDER BY posts.created_at DESC, comments.created_at ASC
    """,
        (user["id"],),
    )

    posts = cursor.fetchall()

    # Prepare the posts data with comments
    grouped_posts = {}
    for post in posts:
        post_id = post["post_id"]
        content_with_links = re.sub(
            r"(#\w+)",
            lambda match: f'<a href="{url_for("hashtags", tag=match.group(1)[1:])}" class="hashtag-links">{match.group(1)}</a>',
            post["content"],
        )
        content_with_links = Markup(content_with_links)
        if post_id not in grouped_posts:
            grouped_posts[post_id] = {
                "post_id": post_id,
                "content": content_with_links,
                "created_at": time_ago(post["created_at"]),  # Format it as needed
                "username": post["post_user"],
                "post_cost":calculate_post_cost(post["like_count"], post["comment_count"]),
                "like_count": post["like_count"],
                "comments": [],
                "is_liked": False,  # Default like state
            }

        # Check if the current user has liked the post
        if "user_id" in session:
            cursor.execute(
                "SELECT * FROM post_likes WHERE post_id = ? AND user_id = ?",
                (post["post_id"], session["user_id"]),
            )
            if cursor.fetchone():
                grouped_posts[post_id]["is_liked"] = True

        # Handle comments for each post
        if post["comment_id"]:
            comment_data = {
                "comment_id": post["comment_id"],
                "username": post["comment_user"],
                "content": post["comment_content"],
                "like_count": post["comment_like_count"],
                "is_liked": False,  # Default comment like state
            }

            # Check if the current user has liked the comment
            if "user_id" in session:
                cursor.execute(
                    "SELECT * FROM comment_likes WHERE comment_id = ? AND user_id = ?",
                    (post["comment_id"], session["user_id"]),
                )
                if cursor.fetchone():
                    comment_data["is_liked"] = True

            grouped_posts[post_id]["comments"].append(comment_data)

    final_posts = list(grouped_posts.values())

    if request.method == "POST":
        # Handle profile update
        new_username = request.form.get("username")
        new_email = request.form.get("email")
        new_bio = request.form.get("bio")

        # Validation for empty fields
        if not new_username or not new_email:
            flash("Username and Email are required!", "error")
            return render_template("profile.html", user=user)

        # Update user data in the database
        cursor.execute(
            """UPDATE users SET username = ?, email = ?, bio = ? WHERE id = ?""",
            (new_username, new_email, new_bio, user["id"]),
        )
        conn.commit()  # Commit the changes to the database

        # Update the session with the new username
        session["username"] = new_username
        flash("Profile updated successfully!", "success")

        conn.close()
        return redirect(url_for("profile"), username=new_username)

    conn.close()
    return render_template(
        "profile.html", username=username, user=user, posts=final_posts, post_num = len(posts)
    )


@app.route("/edit_bio", methods=["GET", "POST"])
def edit_bio():
    # Ensure user is logged in
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = session["user_id"]
    if request.method == "POST":
        # Retrieve the bio input from the form
        bio = request.form.get("bio")
        # Update the user's bio in the database (replace with your update logic)
        cursor.execute("UPDATE users SET bio = ? WHERE id = ?", (bio, user_id))
        # update_user_bio(user_id, bio)
        conn.commit()
        conn.close()
        flash("Bio updated successfully!", "success")
        return redirect(url_for("profile", username=session["username"]))

    return render_template("profile.html")


@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        new_username = request.form.get("username")
        new_password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        user_id = session["user_id"]

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the new username is already taken (if a new one was provided)
        if new_username:
            cursor.execute("SELECT * FROM users WHERE username = ?", (new_username,))
            existing_user = cursor.fetchone()
            if existing_user and existing_user["id"] != user_id:
                flash("This username is already taken. Please choose another one.")
                conn.close()
                return redirect(url_for("edit_profile"))

        # Check if passwords match (if new password was provided)
        if new_password and new_password != confirm_password:
            flash("Passwords do not match.")
            conn.close()
            return redirect(url_for("edit_profile"))

        # Update username if provided and not taken
        if new_username:
            cursor.execute(
                "UPDATE users SET username = ? WHERE id = ?", (new_username, user_id)
            )

        # Update password if provided and confirmed
        if new_password:
            hashed_password = generate_password_hash(
                new_password, method="pbkdf2:sha256"
            )
            cursor.execute(
                "UPDATE users SET password = ? WHERE id = ?", (hashed_password, user_id)
            )

        conn.commit()
        conn.close()

        flash("Profile updated successfully!")
        return redirect(url_for("settings"))

    return render_template("edit_profile.html")


@app.route("/logout")   
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("landing"))


@app.route('/get-perks')
def get_perks():
    # Ensure the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if user not logged in

    user_id = session['user_id']
    db_path = 'talks.db'  # Path to your SQLite database file

    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Execute raw SQL query to fetch perks, last_login_date, and login_streak
    query = """
        SELECT perks, last_login_date, login_streak
        FROM users
        WHERE id = ?
    """
    cursor.execute(query, (user_id,))
    user_data = cursor.fetchone()

    conn.close()

    # Check if user data exists
    if not user_data:
        return "User not found", 404

    # Map the query result to a dictionary for template rendering
    user = {
        "perks": user_data[0],
        "last_login_date": user_data[1],
        "login_streak": user_data[2]
    }

    # Render the get_perks page with user data
    return render_template('get_perks.html', user=user)

@app.route('/premium')
def premium():
    return render_template('premium.html')

@app.route('/')
def user_blogs():
    return render_template('premium.html')

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy/index.html')

@app.route('/privacy-policy/data-collection')
def data_collection():
    return render_template('privacy_policy/data_collection.html')

@app.route('/privacy-policy/cookies')
def cookies():
    return render_template('privacy_policy/cookies.html')

@app.route('/privacy-policy/data-sharing')
def data_sharing():
    return render_template('privacy_policy/data_sharing.html')

@app.route('/privacy-policy/data-protection')
def data_protection():
    return render_template('privacy_policy/data_protection.html')

@app.route('/privacy-policy/user-rights')
def user_rights():
    return render_template('privacy_policy/user_rights.html')

@app.route('/privacy-policy/terms-conditions')
def terms_conditions():
    return render_template('privacy_policy/terms_conditions.html')

@app.route('/privacy-policy/contact')
def pp_contact():
    return render_template('privacy_policy/contact.html')


# Run the application
if __name__ == "__main__":
    app.run(debug=True)
