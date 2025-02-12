from flask import Flask, flash, request, redirect, render_template, send_from_directory, url_for
from werkzeug.utils import secure_filename
import os, random
import numpy as np

app = Flask(__name__)

UPLOAD_FOLDER=os.environ.get('UPLOAD_FOLDER', '../uploads')
BANNED_EXTENSIONS='htm' #everything containing htm
FILENAME_LENGTH=os.environ.get('FILENAME_LENGTH', 4)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['BANNED_EXTENSIONS'] = BANNED_EXTENSIONS
app.config['FILENAME_LENGTH'] = FILENAME_LENGTH

def get_random_string():
    length = app.config['FILENAME_LENGTH']
    rand_num = random.randrange(36**(length-1),36**length) #get base 36 number with filename_length digits
    rand_string = np.base_repr(rand_num, 36).lower() #convert it into base 36 string

    return rand_string

def make_link(base_url, filename):
    delete_right = base_url.rsplit("/", 1)[0]
    link = delete_right + "/uploads/" + filename
    return link

@app.route("/")
def home_page():
    return render_template('index.html')

@app.route("/file", methods=['POST'])
def submit_file():
    if request.method == 'POST':
        if "file" not in request.files:
            flash("No file provided")
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash("No file selected")
            return redirect(request.url)

        filename_array = file.filename.rsplit('.', 1)
        if len(filename_array) > 1:
            extension = filename_array[1].lower() #get extension
        else:
            extension = ".txt" #generic extension
        if app.config['BANNED_EXTENSIONS'] in extension:
            extension = ".txt" #replace XSS vuln with generic extension

        filename = secure_filename(get_random_string() + extension)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        link = make_link(request.base_url, filename)

    return render_template('success.html', link=link)

@app.route("/text", methods=['POST'])
def submit_text():
    if request.method == 'POST':
        if "text" not in request.form:
            flash("No text provided")
            return redirect(request.url)
        text = request.form['text']

        if not text:
            flash("No text provided")
            return redirect(request.url)

        filename = secure_filename(get_random_string() + ".txt")
        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), "w") as file:
            file.write(text)

        link = make_link(request.base_url, filename)

    return render_template('success.html', link=link)

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    if app.config['BANNED_EXTENSIONS'] in filename:
        return "<h1>403 Forbidden</h1>", 403
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
