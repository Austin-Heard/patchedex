import os
import boto3
from flask import Flask, render_template, request
from PIL import Image
from rembg import remove
import cv2
from operator import itemgetter
from skimage.metrics import structural_similarity as ssim
import requests
from celery import Celery

app = Flask(__name__)

def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)
    return celery

app.config.update(
    CELERY_BROKER_URL='amqp://localhost',
)


celery = make_celery(app)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"]
)

s3 = boto3.resource('s3', region_name='us-east-2')
BUCKET = 'tobytether'

@celery.task
def queue(request_image):  
    print("goes through")
    png = '.png'
    slasher = '/'
    presenter = '_bgrm'
    comparisoner = '_cm'
    test_file = request_image[12:]
    test_file.save(os.path.join('UPLOAD_FOLDER', test_file.filename + png))
    file_to_parse = request_image.filename
    masterlist = []
    input = Image.open('UPLOAD_FOLDER' + slasher + file_to_parse)
    output = remove(input)
    output.save(os.path.join('BGRM_FOLDER', test_file.filename + presenter + png))
    s3.Bucket(BUCKET).upload_file('BGRM_FOLDER' + slasher + test_file.filename + presenter + png, "NoBg" + slasher + test_file.filename + presenter + png)
    imageBox = output.getbbox()
    output_boxed = output.crop(imageBox).resize((254,254))
    output_boxed.save(os.path.join('COMPARISON_FOLDER', test_file.filename + comparisoner + png))
    img2 = cv2.imread('COMPARISON_FOLDER' + slasher + test_file.filename + comparisoner + png)
    img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    print("before loop")
    for obj in s3.Bucket(BUCKET).objects.filter(Prefix='Square/'):
        if obj.key == 'Square/':
            continue
        url = 'https://tobytether.s3.us-east-2.amazonaws.com/Square/' + obj.key[7:]
        r = requests.get(url, allow_redirects=True)
        open('TEMP_DOWNLOAD_FOLDER/' + obj.key[7:], 'wb').write(r.content)
        sublist = []
        img1_raw = 'TEMP_DOWNLOAD_FOLDER/' + obj.key[7:]
        img1 = cv2.imread(img1_raw)
        img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        error = ssim(img1, img2)
        sublist = [error, 'https://tobytether.s3.us-east-2.amazonaws.com/NoBg/' + obj.key[7:]]
        masterlist.append(sublist)
    sortedlist = sorted(masterlist, key = itemgetter(0), reverse = True)
    sortedlist = sortedlist[:6]
    returnlist = []
    for i in range(6):
        returnlist.append(sortedlist[i][1])
    returnlist.append('https://tobytether.s3.us-east-2.amazonaws.com/NoBg/' + test_file.filename + presenter + png)
    s3.Bucket(BUCKET).upload_file('COMPARISON_FOLDER' + slasher + test_file.filename + comparisoner + png, "Square" + slasher + test_file.filename + comparisoner + png)
    dir = 'BGRM_FOLDER/'
    for f in os.listdir(dir):
        os.remove(os.path.join(dir, f))
    dir = 'COMPARISON_FOLDER/'
    for f in os.listdir(dir):
        os.remove(os.path.join(dir, f))
    dir = 'TEMP_DOWNLOAD_FOLDER/'
    for f in os.listdir(dir):
        os.remove(os.path.join(dir, f))
    dir = 'UPLOAD_FOLDER/'
    for f in os.listdir(dir):
        os.remove(os.path.join(dir, f))
    return returnlist

@app.route('/', methods = ['POST'])
def upload_file():
    request_image = request.files['Initial_Patch']
    request_image.save(os.path.join('UPLOAD_FOLDER', request_image.filename + '.png'))
    queue.delay('UPLOAD_FOLDER/' + request_image.filename + '.png')
    return "HI"

@app.route('/', methods = ['PUT'])
def upload_file():
    request_image = request.files['Initial_Patch']
    request_image.save(os.path.join('UPLOAD_FOLDER', request_image.filename + '.png'))
    queue('UPLOAD_FOLDER/' + request_image.filename + '.png')
    return "HI"
        

app.run(debug=True, host="0.0.0.0", port=8080)

