import pytesseract
import os
from PIL import Image
import glymur
#direct tesseract lib location
pytesseract.pytesseract.tesseract_cmd = r'E:\Tesseract\tesseract.exe'

# File and folder paths for sample set
FOLDER_PATH = r'Sample set'

def detectText(img):
    #if the file end with jp2, the thesseract not support jp2 
    if img.lower().endswith('.jp2'):
        # Use Glymur to read the JP2 file
        jp2 = glymur.Jp2k(img)
        img_data = jp2[:]
        # Convert the image data to a PIL Image
        with Image.fromarray(img_data) as opened_image:
            result = pytesseract.image_to_string(opened_image)
    else:
        result = pytesseract.image_to_string(img)
    return result

filenames = next(os.walk(FOLDER_PATH))[2]
#process all images from folder and return text file for each images
for file in filenames:
    temp_file = file.split(".")
    file_path = temp_file[0]+'.txt'
    df = detectText(os.path.join(FOLDER_PATH, file))
    with open(file_path, 'w') as file:
        file.write(df)
