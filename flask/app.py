from flask import Flask, flash, request, redirect, render_template, send_file, url_for, jsonify
from flask_pymongo import PyMongo
from gridfs import GridFS, GridFSBucket
from werkzeug.utils import secure_filename
import os, random, io, qrcode, base64
import numpy as np
from datetime import datetime, timedelta
from bson import ObjectId
from io import BytesIO
from pymongo.errors import DuplicateKeyError
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

#default values
#UPLOAD_FOLDER='../uploads'
BANNED_EXTENSIONS='htm' #everything containing htm
FILENAME_LENGTH=4
MONGO_CONN="mongodb://mongo:27017/fsharer"

#app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', UPLOAD_FOLDER)
app.config['BANNED_EXTENSIONS'] = os.environ.get('BANNED_EXTENSIONS', BANNED_EXTENSIONS)
app.config['FILENAME_LENGTH'] = os.environ.get('FILENAME_LENGTH', FILENAME_LENGTH)
app.config['MONGO_URI'] = os.environ.get("MONGO_CONN", MONGO_CONN)

mongo = PyMongo(app)
mongofs = GridFS(mongo.db)

def get_random_string():
    length = app.config['FILENAME_LENGTH']
    rand_num = random.randrange(36**(length-1),36**length) #get base 36 number with filename_length digits
    rand_string = np.base_repr(rand_num, 36).lower() #convert it into base 36 string

    return rand_string

def make_link(base_url, filename):
    delete_right = base_url.rsplit("/", 1)[0]
    link = delete_right + "/uploads/" + filename
    return link

def generate_qrcode(link):
    qr = qrcode.QRCode(
        box_size=10,
        border=4
    )
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color=(231,220,188))

    img_io = io.BytesIO()
    img.save(img_io, format="PNG")
    img_io.seek(0)
    qr_base64 = base64.b64encode(img_io.getvalue()).decode("utf-8")

    return qr_base64

def purge_files():
    fs = GridFSBucket(mongo.db)
    cutoff = datetime.utcnow() - timedelta(hours=12)
    to_delete = mongo.db["fs.files"].find({"time":{"$lt": cutoff}})

    for file in to_delete:
        fs.delete(file["_id"])

scheduler = BackgroundScheduler()
scheduler.add_job(purge_files, "interval", minutes=5)
scheduler.start()

@app.route("/")
def home_page():
    return render_template('index.html')

@app.route("/file", methods=['POST'])
def submit_file():
    if request.method == 'POST':
        if "file" not in request.files:
            #flash("No file provided") #Needs fix
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            #flash("No file selected") #Needs fix
            return redirect(request.url)

        filename_array = file.filename.rsplit('.', 1)
        if len(filename_array) > 1:
            extension = filename_array[1].lower() #get extension
        else:
            extension = "txt" #generic extension
        if app.config['BANNED_EXTENSIONS'] in extension:
            extension = "txt" #replace XSS vuln with generic extension

        attempts = 0

        #attempt to give the file a random name. Keep retrying if duplicate key, with a limit
        while attempts < 10:
            rand = get_random_string()
            filename = secure_filename(rand + "." + extension)

            #Use mongodb instead
            try:
                file_id = mongofs.put(file, filename=filename, _id=rand, time=datetime.utcnow())
                attempts = 10
            except DuplicateKeyError:
                attempts += 1
                pass

            #file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        link = make_link(request.base_url, filename)

    return render_template('success.html', link=link, qrcode=generate_qrcode(link))

@app.route("/text", methods=['POST'])
def submit_text():
    if request.method == 'POST':
        if "text" not in request.form:
            #flash("No text provided")
            return redirect(request.url)
        text = request.form['text']

        if not text:
            #flash("No text provided")
            return redirect(request.url)

        file = text.encode("utf-8")

        #try to get random name and save to mongodb
        attempts = 0
        while attempts < 10:
            rand = get_random_string()
            filename = secure_filename(rand + ".txt")

            try:
                file_id = mongofs.put(file, filename=filename, _id=rand, time=datetime.utcnow())
                attempts = 10
            except DuplicateKeyError:
                attempts += 1
                pass
        #with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), "w") as file:
        #    file.write(text)

        link = make_link(request.base_url, filename)

    return render_template('success.html', link=link, qrcode=generate_qrcode(link))

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    if "." + app.config['BANNED_EXTENSIONS'] in filename:
        return "<h1>403 Forbidden</h1>", 403
    file = mongofs.get(filename.rsplit(".", 1)[0])
    return send_file(BytesIO(file.read()), download_name=file.filename, as_attachment=False)
    #return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
