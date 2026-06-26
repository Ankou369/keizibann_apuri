from flask import Flask, render_template, request, redirect, g
import sqlite3
from flask import send_from_directory
#ログイン
from flask_login import UserMixin, LoginManager, login_required, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
DATABASE="bulletin_board_app.db"

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

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

### ログイン ############################

# セッションに保存されているユーザーIDから、ログイン中のユーザーを復元する関数
# ログインした後にページを移動してもログイン状態を維持するために必要な関数
@login_manager.user_loader
def load_user(userid):
    return User(userid)

#「ログインしていない人がログイン必須ページにアクセスしたらどうするか」を決める関数
# ログインしていない人がログイン必須ページにアクセスしたときは、ログインページにリダイレクトするように設定
@login_manager.unauthorized_handler
def unauthorized():
    return redirect('/login')

# signupの処理
# GET:登録画面を表示, POST:登録内容を受けとる
@app.route("/signup", methods=['GET', 'POST'])
def signup():
    # エラーメッセージを格納する変数（最初は空）
    error_message = ''

    #ユーザーが<form method="POST">で送信した場合だけ実行される
    if request.method == 'POST':
        # <input name="userid">からユーザIDを取得
        userid = request.form.get('userid')
        # <input name="password">からパスワードを取得
        password = request.form.get('password')
        # パスワードをハッシュ化
        pass_hash = generate_password_hash(password)

        # データベースに接続
        db = get_db()
        # すでに同じユーザIDが存在するか確認
        user_check = get_db().execute("select userid from user where userid=?", [userid,]).fetchall()
        #同じユーザIDが存在しない場合
        if not user_check:
            #ユーザIDとハッシュ化したパスワードをデータベースに保存
            db.execute(
                "insert into user (userid,password) values(?,?)",
                [userid,pass_hash]
            )
            db.commit()
            return redirect('/login')
        else:
            error_message = '入力されたユーザIDはすでに利用されています'
    
    return render_template('signup.html', error_message=error_message)

# loginの処理
# GET:ログイン画面を表示, POST:ログイン処理
@app.route("/login", methods=['GET', 'POST'])
def login():
    error_message = ''
    # ログイン失敗時に入力されたユーザIDを保持するための変数
    userid = ''

    # ログインボタンが押されたら実行
    if request.method == 'POST':
        # <input name="userid">からユーザIDを取得
        userid = request.form.get('userid')
        # <input name="password">からパスワードを取得
        password = request.form.get('password')
    
        #ログインのチェック
        user_data = get_db().execute(
            "select password from user where userid=?",[userid,]
        ).fetchone()
        # ユーザIDが存在するか確認
        if user_data is not None:
            # パスワードが正しいか確認
            if check_password_hash(user_data[0],password):
                user = User(userid)
                login_user(user)
                return redirect('/')
        
        error_message = '入力されたIDもしくはパスワードが誤っています'

    return render_template('login.html', userid=userid, error_message=error_message)

@app.route("/logout", methods=['GET'])
def logout():
    # Flask-Loginのlogout_user()を呼び出すことで、ログアウト処理を行う
    logout_user()
    return redirect('/login')

###########################


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    # フォームが送信されたときの処理
    if request.method == "POST":
        # <input name="title">からタイトルを取得
        title = request.form["title"]
        # <input name="comment">からコメントを取得
        comment = request.form["comment"]
        # <input name="image">から画像を取得
        image = request.files["image"]

        filename = None

        # 画像が選択されている場合は、画像を保存
        if image and image.filename != "":
            filename = image.filename

            image.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

        db = get_db()
        # 投稿を保存
        db.execute(
            """
            INSERT INTO post(title, comment, image, userid)
            VALUES (?, ?, ?, ?)
            """,
            (title, comment, filename, current_user.id)
        )

        db.commit()

        return redirect("/")

    search = request.args.get("search", "")

    if search:
        db = get_db()
        posts = db.execute(
            """
            SELECT *
            FROM post
            WHERE comment LIKE ?
            ORDER BY id DESC
            """,
            (f"%{search}%",)
        ).fetchall()
    else:
        db = get_db()
        # 投稿一覧を取得
        posts = db.execute(
            """
            SELECT *
            FROM post
            ORDER BY id DESC
            """
        ).fetchall()

    db = get_db()

    # フォローしているユーザーのIDを取得
    follow_list = db.execute(
        """
        SELECT following_id
        FROM follow_table
        WHERE follower_id = ?
        """,
        (current_user.id,)
    ).fetchall()

    #follow_list[0]["following_id"]の形で取得できるので、following_idだけのリストに変換
    for i, row in enumerate(follow_list):
        follow_list[i] = row["following_id"]

    return render_template(
        "index.html",
        posts=posts,
        follow_list=follow_list,
        search=search
    )

@app.route("/reset", methods=['POST'])
def reset():
    db = get_db()
    id = request.form.get("id")
    db.execute("DELETE FROM post WHERE id=? AND userid=?",(id, current_user.id))
    db.commit()
    return redirect('/')

@app.route("/uploads/<filename>")
@login_required
def uploaded_file(filename):
    # 指定したフォルダからファイルを取り出してブラウザへ送る関数
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )

@app.route("/follow", methods=["POST"])
def follow():
    # フォローするユーザーのIDを取得
    follow_userid = request.form.get("follow_userid")

    db = get_db()
    result = db.execute(
        """
        SELECT EXISTS(
            SELECT 1
            FROM follow_table
            WHERE follower_id = ? AND following_id = ?
        )""",
        (current_user.id, follow_userid)
    ).fetchone()
    db.commit()

    if result[0] == True:
        # すでにフォローしている場合は、フォローを解除する
        db = get_db()
        db.execute(
            """
            DELETE FROM follow_table
            WHERE follower_id = ? AND following_id = ?
            """,
            (current_user.id, follow_userid)
        )
        db.commit()
        return redirect('/')
    else:
        # フォロー関係をデータベースに保存
        db = get_db()
        db.execute(
            """
            INSERT INTO follow_table (follower_id, following_id)
            VALUES (?, ?)
            """,
            (current_user.id, follow_userid)
        )
        db.commit()

    return redirect('/')

@app.route("/myaccount")
def myaccount():
    search = request.args.get("search", "")

    if search:
        db = get_db()
        posts = db.execute(
            """
            SELECT *
            FROM post
            WHERE userid = ? AND comment LIKE ?
            ORDER BY id DESC
            """,
            (current_user.id, f"%{search}%")
        ).fetchall()
    else:
        db = get_db()
        # 投稿一覧を取得
        posts = db.execute(
            """
            SELECT *
            FROM post
            WHERE userid = ?
            ORDER BY id DESC
            """,
            (current_user.id,)
        ).fetchall()

    return render_template("myaccount.html",
                           posts=posts,
                           search=search)

@app.route("/fuga")
def fuga():
    return render_template("fuga.html")

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