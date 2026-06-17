from flask import Flask, render_template, request, redirect
from flask import send_from_directory
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

posts = []

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
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
def uploaded_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )

if __name__ == "__main__":
    app.run(debug=True)