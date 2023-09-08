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
from redis import Redis

app = Flask(__name__)

s3 = boto3.resource('s3', region_name='us-east-2')
BUCKET = 'tobytether'

def pull_from_Square():
    for obj in s3.Bucket(BUCKET).objects.filter(Prefix='Square/'):
        if obj.key == 'Square/':
            continue
        url = 'https://tobytether.s3.us-east-2.amazonaws.com/Square/' + obj.key[7:]
        r = requests.get(url, allow_redirects=True)
        open('COMPARISON_FOLDER/' + obj.key[7:], 'wb').write(r.content)

@app.route('/', methods = ['POST'])
def upload_file():
    request_image = request.files['Initial_Patch']
    png = '.png'
    slasher = '/'
    presenter = '_bgrm'
    comparisoner = '_cm'
    request_image.save(os.path.join('UPLOAD_FOLDER', request_image.filename + png))
    file_to_parse = request_image.filename
    masterlist = []
    input = Image.open('UPLOAD_FOLDER' + slasher + file_to_parse + png)
    output = remove(input)
    output.save(os.path.join('BGRM_FOLDER', file_to_parse + presenter + png))
    s3.Bucket(BUCKET).upload_file('BGRM_FOLDER' + slasher + file_to_parse + presenter + png, "NoBg" + slasher + file_to_parse + presenter + png)
    
    imageBox = output.getbbox()
    output_boxed = output.crop(imageBox).resize((254,254))
    output_boxed.save(os.path.join('COMPARISON_FOLDER', file_to_parse + comparisoner + png))
    
    img2 = cv2.imread('COMPARISON_FOLDER' + slasher + file_to_parse + comparisoner + png)
    img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    for filename in os.listdir('COMPARISON_FOLDER/'):
        sublist = []
        img1_raw = 'COMPARISON_FOLDER/' + filename
        img1 = cv2.imread(img1_raw)
        img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        error = ssim(img1, img2)
        sublist = [error, 'https://tobytether.s3.us-east-2.amazonaws.com/NoBg/' + filename[:-7] + presenter + png]
        masterlist.append(sublist)
    sortedlist = sorted(masterlist, key = itemgetter(0), reverse = True)
    num_suggestions = 6
    sortedlist = sortedlist[:num_suggestions]
    returnlist = []
    for i in range(num_suggestions):
        returnlist.append(sortedlist[i][1])
    returnlist.append('https://tobytether.s3.us-east-2.amazonaws.com/NoBg/' + file_to_parse + presenter + png)
    s3.Bucket(BUCKET).upload_file('COMPARISON_FOLDER' + slasher + file_to_parse + comparisoner + png, "Square" + slasher + file_to_parse + comparisoner + png)
    dir = 'BGRM_FOLDER/'
    os.remove(dir + request_image.filename + presenter + png)
    dir = 'UPLOAD_FOLDER/'
    os.remove(dir + request_image.filename + png)
    return returnlist

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)

