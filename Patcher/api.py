import os
import boto3
from flask import Flask, render_template, request, flash, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from PIL import Image
from rembg import remove
import cv2
from operator import itemgetter
import IPython.display as display
from skimage.metrics import structural_similarity as ssim
import requests

app = Flask(__name__)

s3 = boto3.resource('s3', region_name='us-east-2')
BUCKET = 'tobytether'

@app.route('/', methods = ['GET','POST'])
def upload_file():
    if request.method == 'POST':
        png = '.png'
        slasher = '/'
        presenter = '_bgrm'
        comparisoner = '_cm'
        test_file = request.files['Initial_Patch']
        test_file.save(os.path.join('UPLOAD_FOLDER', test_file.filename + png))
        file_to_parse = test_file.filename + png
        masterlist = []
        input = Image.open('UPLOAD_FOLDER' + slasher + file_to_parse)
        output = remove(input)
        output.save(os.path.join('BGRM_FOLDER', test_file.filename + presenter + png))
        s3.Bucket(BUCKET).upload_file('BGRM_FOLDER' + slasher + test_file.filename + presenter + png, "NoBg" + slasher + test_file.filename + presenter + png)
        imageBox = output.getbbox()
        output_boxed = output.crop(imageBox).resize((254,254))
        output_boxed.save(os.path.join('COMPARISON_FOLDER', test_file.filename + comparisoner + png))
        variable = s3.Bucket(BUCKET).upload_file('COMPARISON_FOLDER' + slasher + test_file.filename + comparisoner + png, "Square" + slasher + test_file.filename + presenter + png)
        img2 = cv2.imread('COMPARISON_FOLDER' + slasher + test_file.filename + comparisoner + png)
        img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        # send_variable = 'https://tobytether.s3.us-east-2.amazonaws.com/NoBg/' + test_file.filename + presenter + png
        # return send_variable
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
        returnlist.append('https://tobytether.s3.us-east-2.amazonaws.com/NoBg/' + test_file.filename + png)
        return returnlist
    else:
        return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)