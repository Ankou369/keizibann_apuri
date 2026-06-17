from flask import Flask, render_template, request, redirect, g
import sqlite3
from flask import send_from_directory
#ログイン
from flask_login import UserMixin, LoginManager, login_required, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
DATABASE="account.db"

import os

app = Flask(__name__)
app.secret_key = os.urandom(24)
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, userid):
        self.id = userid

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

posts = []

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

##ログイン
@login_manager.user_loader
def load_user(userid):
    return User(userid)

@login_manager.unauthorized_handler
def unauthorized():
    return redirect('/login')

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    error_message = ''
    if request.method == 'POST':
        userid = request.form.get('userid')
        password = request.form.get('password')
        pass_hash = generate_password_hash(password)

        db = get_db()
        user_check = get_db().execute("select userid from user where userid=?", [userid,]).fetchall()
        if not user_check:
            db.execute(
                "insert into user (userid,password) values(?,?)",
                [userid,pass_hash]
            )
            db.commit()
            return redirect('/login')
        else:
            error_message = '入力されたユーザIDはすでに利用されています'
    
    return render_template('signup.html', error_message=error_message)

@app.route("/login", methods=['GET', 'POST'])
def login():
    error_message = ''
    userid = ''

    if request.method == 'POST':
        userid = request.form.get('userid')
        password = request.form.get('password')
        #ログインのチェック
        user_data = get_db().execute(
            "select password from user where userid=?",[userid,]
        ).fetchone()
        if user_data is not None:
            if check_password_hash(user_data[0],password):
                user = User(userid)
                login_user(user)
                return redirect('/')
        
        error_message = '入力されたIDもしくはパスワードが誤っています'

    return render_template('login.html', userid=userid, error_message=error_message)

@app.route("/logout", methods=['GET'])
def logout():
    logout_user()
    return redirect('/login')
###

@app.route("/", methods=["GET", "POST"])
@login_required
def index():

    if request.method == "POST":
        title = request.form["title"]
        comment = request.form["comment"]

        image = request.files["image"]

        filename = image.filename
        image.save(
            os.path.join(app.config["UPLOAD_FOLDER"], filename)
        )

        posts.append({
            "title": title,
            "comment": comment,
            "image": filename
        })

        return redirect("/")

    return render_template("index.html", posts=posts)

@app.route("/uploads/<filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )

if __name__ == "__main__":
    app.run(debug=True)

#database
def connect_db():
    rv = sqlite3.connect(DATABASE)
    rv.row_factory = sqlite3.Row
    return rv
def get_db():
    if not hasattr(g,'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db