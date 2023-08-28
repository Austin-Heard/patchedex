import os
import boto3
from flask import Flask, render_template, request
from PIL import Image
from rembg import remove
import cv2
from operator import itemgetter
from skimage.metrics import structural_similarity as ssim
import requests
# These are the required imports. I recommend working on this in a Pythonic environment and downloading 
# the required libraries to your local machine using pip. I haven't worked on this in anything other than 
# a pythonic environment so I can't guarantee success otherwise

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
        #The four variables above help me contatinte the file and url names for saving and retrieving. I've had problems
        # incorporating '/' in strings before so I keep it as its own variable
        test_file = request.files['Initial_Patch']
        test_file.save(os.path.join('UPLOAD_FOLDER', test_file.filename + png))
        #The two above lines of code take the posted file and put it in a temporary folder, also forcing it into a png format
        file_to_parse = test_file.filename + png
        #This variable just helps call from the local folder easier
        masterlist = []
        #The masterlist variable will ultimately be filled of sublists that have two elements: the url and the similarity
        # associated with the url. This will make more sense lower down
        input = Image.open('UPLOAD_FOLDER' + slasher + file_to_parse)
        output = remove(input)
        output.save(os.path.join('BGRM_FOLDER', test_file.filename + presenter + png))
        #The above lines of code take from the temporary folder and make a new file that has the background removed
        # then saves that file to a different local folder
        s3.Bucket(BUCKET).upload_file('BGRM_FOLDER' + slasher + test_file.filename + presenter + png, "NoBg" + slasher + test_file.filename + presenter + png)
        #This line just contatinates the folder locations into the bucket location. It saves from the local folder into the AWS
        # bucket that has the other images with their backgrounds removed
        imageBox = output.getbbox()
        output_boxed = output.crop(imageBox).resize((254,254))
        output_boxed.save(os.path.join('COMPARISON_FOLDER', test_file.filename + comparisoner + png))
        #The above lines of code do a similar operation to removing the background and saving to a local folder, only it
        # it takes from background removed folder and puts it into a comparison folder. It puts everything to the same size
        # so they may be adequetely compared.
        #The file is not saved to the AWS Bucket yet, otherwise it would inevitably be compared with itself. This line of code
        # is featured toward the end of this function
        img2 = cv2.imread('COMPARISON_FOLDER' + slasher + test_file.filename + comparisoner + png)
        img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        #These lines of code prep the initial patch to be compared
        for obj in s3.Bucket(BUCKET).objects.filter(Prefix='Square/'):
        #This for loop looks for all the items in the bucket that we're using under the folder named 'Square'. These are
        # the comparison files. Ultimately, they'll all be temporarily downloaded to be compared
            if obj.key == 'Square/':
                continue
            #An odd aspect of AWS is that it will try to use the 'Square' folder itself as its first iteration, this 
            # conditional above will skip it as a first step
            url = 'https://tobytether.s3.us-east-2.amazonaws.com/Square/' + obj.key[7:]
            r = requests.get(url, allow_redirects=True)
            open('TEMP_DOWNLOAD_FOLDER/' + obj.key[7:], 'wb').write(r.content)
            #These three lines of code will get the url of the file associated with its position in the bucket. The
            # obj.key[7:] object is the name of the file without a 'Square/' in front of it
            sublist = []
            #The sublist will be the url combined with how similar it is to the upload folder. All the sublists will
            # be added to the masterlist
            img1_raw = 'TEMP_DOWNLOAD_FOLDER/' + obj.key[7:]
            img1 = cv2.imread(img1_raw)
            img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            #These three lines of code prep the comparison file to be compared to the upload file
            error = ssim(img1, img2)
            #This error is associated with how similar the two images are. The higher the error, the more similar the files
            sublist = [error, 'https://tobytether.s3.us-east-2.amazonaws.com/NoBg/' + obj.key[7:]]
            masterlist.append(sublist)
            #The master list will have as many sublists as there are runs through the for loop, with each run being a different
            # file to be compared. They will all have an error associated with them and the ones with the highest error will
            # be the ones that look most similar to the upload file. Ultimately, it will hopefully find patches that are the
            # same variety as the patch that was uploaded. The patches that it shows the user are the ones with their backgrounds
            # removed, not the ones prepped for comparison
        sortedlist = sorted(masterlist, key = itemgetter(0), reverse = True)
        #Sorts by highest error
        sortedlist = sortedlist[:6]
        #Cuts off at the six patches with the highest error
        returnlist = []
        for i in range(6):
            returnlist.append(sortedlist[i][1])
        #New list has all the url's associated with the six highest error patches in the database
        returnlist.append('https://tobytether.s3.us-east-2.amazonaws.com/NoBg/' + test_file.filename + presenter + png)
        #This adds the original ptch at the very end so the user has the option of selecting their own, in the event theirs is
        # the first one of its variety added to the database
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
        #These lines of code purge the temporary folders of their contents for the next run-through
        s3.Bucket(BUCKET).upload_file('COMPARISON_FOLDER' + slasher + test_file.filename + comparisoner + png, "Square" + slasher + test_file.filename + comparisoner + png)
        #This is the line of code that was mentioned above that was put down below. It is put here so the patch does not compare
        # itself to itself when is run through, but still put into the AWS database for future runs
        return returnlist
    else:
        return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
