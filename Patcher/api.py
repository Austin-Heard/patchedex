# import os
# import boto3
# from flask import Flask, render_template, request, flash, redirect, jsonify
# from flask_sqlalchemy import SQLAlchemy
# from PIL import Image
# from rembg import remove
# import cv2
# from operator import itemgetter
# import IPython.display as display
# from skimage.metrics import structural_similarity as ssim
# import tempfile

# app = Flask(__name__)

# s3 = boto3.resource('s3')
# BUCKET = 'tobytether'

# @app.route('/', methods = ['GET','POST'])
# def upload_file():
#     if request.method == 'POST':
#         png = '.png'
#         slasher = '/'
#         presenter = '_bgrm'
#         comparisoner = '_cm'
#         test_file = request.files['Initial_Patch']
#         test_file.save(os.path.join('UPLOAD_FOLDER', test_file.filename + png))
#         file_to_parse = test_file.filename + png
#         masterlist = []
#         input = Image.open('UPLOAD_FOLDER' + slasher + file_to_parse)
#         output = remove(input)
#         output.save(os.path.join('BGRM_FOLDER', test_file.filename + presenter + png))
#         s3.Bucket(BUCKET).upload_file('BGRM_FOLDER' + slasher + test_file.filename + presenter + png, "NoBg" + slasher + test_file.filename + presenter + png)
#         imageBox = output.getbbox()
#         output_boxed = output.crop(imageBox).resize((254,254))
#         output_boxed.save(os.path.join('COMPARISON_FOLDER', test_file.filename + comparisoner + png))
#         variable = s3.Bucket(BUCKET).upload_file('COMPARISON_FOLDER' + slasher + test_file.filename + comparisoner + png, "Square" + slasher + test_file.filename + presenter + png)
        # img2 = cv2.imread('COMPARISON_FOLDER' + slasher + test_file.filename + comparisoner + png)
        # img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        # sqs = boto3.resource('sqs')
        # for queue in sqs.queues.all():
        #     print(queue.url)
        # for bucket in s3.buckets.all():
        #     for obj in bucket.objects.filter(Prefix='Square/'):
        #         print('{0}:{1}'.format(bucket.name, obj.key))
        # for i in os.listdir('COMPARISON_FOLDER'):
        #     sublist = []
        #     img1_raw = 'COMPARISON_FOLDER' + slasher + i
        #     img1 = cv2.imread(img1_raw)
        #     img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        #     error = ssim(img1, img2)
        #     sublist = [error,img1_raw]
        #     masterlist.append(sublist)
        # sortedlist = sorted(masterlist, key = itemgetter(0), reverse = True)
        # sortedlist = sortedlist[:6]
        # return sortedlist
#         return variable
#     else:
#         return render_template('index.html')

# if __name__ == "__main__":
#     app.run(debug=True)

from flask import Flask, request, jsonify
import boto3
from rembg import remove
import os

app = Flask(__name__)
s3 = boto3.resource('s3')
bucket_name = 'toby-tether'
input_folder = 'Patch/'
output_folder = 'NoBg/'

@app.route('/process-image', methods=['POST'])
def process_image():
    data = request.get_json()
    filename = data.get('filename')
    print(filename)
    if not filename:
        return jsonify({"error": "filename is required"}), 400

    s3_path = f"{input_folder}{filename}"
    local_path = f"tether/Patcher/BGRM_FOLDER/{filename}"
    try:
        s3.Bucket(bucket_name).download_file(s3_path, local_path)
    except boto3.exceptions.botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return jsonify({"error": f"File {filename} not found in S3 bucket"}), 404
        else:
            return jsonify({"error": "An error occurred accessing S3"}), 500


    with open(local_path, 'rb') as f:
        output = remove(f.read())

    processed_filename = f'processed_{filename}'
    with open(processed_filename, 'wb') as o:
        o.write(output)

    s3_output_path = f"{output_folder}{processed_filename}"
    s3.Bucket(bucket_name).upload_file(processed_filename, s3_output_path)

    image_url = f"https://{bucket_name}.us-east-2.amazonaws.com/{s3_output_path}"

    os.remove(local_path)
    os.remove(processed_filename)

    return jsonify({"image_url": image_url})

if __name__ == '__main__':
    app.run(debug=False)
			