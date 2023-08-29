import os
import boto3
from flask import Flask, render_template, request
from PIL import Image
from rembg import remove
import cv2
from operator import itemgetter
from skimage.metrics import structural_similarity as ssim
import requests
from rq import Queue
from redis import Redis
from pizza import queue

# These are the required imports. I recommend working on this in a Pythonic environment and downloading 
# the required libraries to your local machine using pip. I haven't worked on this in anything other than 
# a pythonic environment so I can't guarantee success otherwise

app = Flask(__name__)

@app.route('/', methods = ['GET','POST'])
def upload_file():
    if request.method == 'POST':
        q = Queue(connection=Redis())
        result = q.enqueue(queue)

if __name__ == "__main__":
    app.run(debug=True)