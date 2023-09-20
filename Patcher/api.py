import os
import boto3
from flask import Flask, request
from PIL import Image
from rembg import remove
import cv2
from operator import itemgetter
from skimage.metrics import structural_similarity as ssim
import requests

app = Flask(__name__)

s3 = boto3.resource('s3', region_name='us-east-2')
BUCKET = 'af-tether'



def clean_folders():
    dir = 'BGRM_FOLDER/'
    for f in os.listdir(dir):
        os.remove(os.path.join(dir, f))
    dir = 'COMPARISON_FOLDER/'
    for f in os.listdir(dir):
        os.remove(os.path.join(dir, f))
    dir = 'UPLOAD_FOLDER/'
    for f in os.listdir(dir):
        os.remove(os.path.join(dir, f))
    for obj in s3.Bucket(BUCKET).objects.filter(Prefix='Square/'):
        if obj.key == 'Square/':
            continue
        url = 'https://af-tether.s3.us-east-2.amazonaws.com/Square/' + obj.key[7:]
        r = requests.get(url, allow_redirects=True)
        open('COMPARISON_FOLDER/' + obj.key[7:], 'wb').write(r.content)



@app.route('/', methods = ['POST'])
def upload_file():
    image_raw = request.files['Initial_Patch']
    file_to_parse = image_raw.filename
    print('Upload: ' + file_to_parse)
    
    png = '.png'
    bgrm_ext = '_bgrm'
    cm_ext = '_cm'

    # save raw image
    upload_path = os.path.join('UPLOAD_FOLDER', file_to_parse + png)
    image_raw.save(upload_path)

    # remove backgroud with BGRM
    image_uploaded = Image.open(upload_path)
    image_uploaded = remove(input)
    print('BGRM: ' + file_to_parse)

    # crop the image per BGRM bounding box, the save locall and S3
    bgrm_path = os.path.join('BGRM_FOLDER', file_to_parse + bgrm_ext + png)
    imageBox = image_uploaded.getbbox()
    output_cropped = image_uploaded.crop(imageBox)
    output_cropped.save(bgrm_path)
    s3.Bucket(BUCKET).upload_file(bgrm_path)
    
    # create comparison image
    comp_path = os.path.join('COMPARISON_FOLDER', file_to_parse + cm_ext + png)
    output_resized = output_cropped.resize((254,254))
    output_resized.save(comp_path)
    s3.Bucket(BUCKET).upload_file(comp_path)
    
    # do comparisons to generate similar image suggestions
    original_image = cv2.imread(comp_path)
    original_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)

    # do comparisons to generate similar image suggestions
    print('before for loop ' + file_to_parse)
    masterlist = []
    for filename in os.listdir('COMPARISON_FOLDER/'):
        if filename == file_to_parse:
            continue
        sublist = []
        comparison_image_raw = 'COMPARISON_FOLDER/' + filename
        comparison_image = cv2.imread(comparison_image_raw)
        comparison_image = cv2.cvtColor(comparison_image, cv2.COLOR_BGR2GRAY)
        error = ssim(comparison_image, original_image)
        sublist = [error, 'https://af-tether.s3.us-east-2.amazonaws.com/NoBg/' + filename[:-7] + bgrm_ext + png]
        masterlist.append(sublist)

    # sort and arrange suggestions images
    sortedlist = sorted(masterlist, key = itemgetter(0), reverse = True)
    num_suggestions = 6
    sortedlist = sortedlist[:num_suggestions]
    returnlist = []
    print('compared ' + file_to_parse)
    for i in range(num_suggestions):
        returnlist.append(sortedlist[i][1])
    returnlist.append('https://af-tether.s3.us-east-2.amazonaws.com/NoBg/' + file_to_parse + bgrm_ext + png)
    dir = 'BGRM_FOLDER/'
    os.remove(dir + file_to_parse + bgrm_ext + png)
    dir = 'UPLOAD_FOLDER/'
    os.remove(dir + file_to_parse + png)
    return returnlist



#if __name__ == "__main__":
clean_folders()
app.run(debug=True, host="0.0.0.0", port=8080, processes=100, threaded=False)

