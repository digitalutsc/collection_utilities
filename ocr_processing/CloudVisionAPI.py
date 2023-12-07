import io
import os
from google.cloud import vision
from google.cloud.vision_v1 import types
import pandas as pd
from PIL import Image
import glymur
#ignore warning, can be remove
import warnings
warnings.filterwarnings("ignore")

# File and folder paths
FOLDER_PATH = r'Sample set'

# Set the path to your Google Cloud credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r'calm-grid-399921-ccadcf1fda86.json'

# Initialize the client for the Vision API
client = vision.ImageAnnotatorClient()

def detectText(img):
    # Check if the file is a JP2 file
    if img.lower().endswith('.jp2'):
        # Use Glymur to read the JP2 file
        jp2 = glymur.Jp2k(img)
        img_data = jp2[:]
        # Convert the image data to a PIL Image
        with Image.fromarray(img_data) as opened_image:
            with io.BytesIO() as output:
                # Convert to JPEG format
                opened_image.save(output, format="JPEG")
                content = output.getvalue()
    else:
        # For non-JP2 files, process normally
        with Image.open(img) as opened_image:
            if opened_image.format != 'JPEG':
                with io.BytesIO() as output:
                    opened_image.convert('RGB').save(output, format="JPEG")
                    content = output.getvalue()
            else:
                with io.open(img, 'rb') as image_file:
                    content = image_file.read()

    # Prepare the image for the Vision API
    image = types.Image(content=content)

    # Perform text detection
    response = client.text_detection(image=image)
    texts = response.text_annotations

    # Create a DataFrame to hold the results
    df = pd.DataFrame(columns=['locale', 'description'])
    for text in texts:
        df = df.append(
            {
                'locale': text.locale,
                'description': text.description
            },
            ignore_index=True
        )
    return df 

# comver dataframe to paragraph
def dataframe_to_paragraph(df):
    # Initialize an empty string for the paragraph
    paragraph = ""

    # Iterate through the DataFrame rows
    for index, row in df.iterrows():
        # Add the description to the paragraph
        paragraph += str(row['description']) + " "

    # Return the combined paragraph
    return paragraph.strip()


#read all image file from FOLDER_PATH
'''
['61220_utsc34299_34907.tiff', '61220_utsc34299_34909.tiff', '61220_utsc34299_34910.tiff', '61220_utsc34299_34911.tiff', '61220_utsc34299_34912.tiff', '61220_utsc34299_34913.tiff', '61220_utsc34299_34914.tiff', '61220_utsc34299_34915.tiff', '61220_utsc34818_17304.jpg', '61220_utsc34818_17305.jpg', '61220_utsc34818_17306.jpg', '61220_utsc34818_17307.jpg', '61220_utsc34818_17308.jpg', '61220_utsc34818_17309.jpg', '61220_utsc34818_17310.jpg', '61220_utsc34818_17311.jpg', '61220_utsc34827_17234.jpg', '61220_utsc34827_17235.jpg', '61220_utsc34827_17236.jpg', 
'61220_utsc34827_17237.jpg', '61220_utsc37954_12863.jp2', '61220_utsc39005_1458.jp2', '61220_utsc39005_1459.jp2', '61220_utsc66350_6012.jpg', '61220_utsc66350_6013.jpg', '61220_utsc73966_24569.jp2', '61220_utsc73966_24570.jp2', '61220_utsc73995_24362.jp2', '61220_utsc73995_24363.jp2']
'''


filenames = next(os.walk(FOLDER_PATH))[2]
#process all images from folder and return text file for each images
for file in filenames:
    temp_file = file.split(".")
    file_path = temp_file[0]+'.txt'
    df = detectText(os.path.join(FOLDER_PATH, file))
    paragraph = dataframe_to_paragraph(df)
    with open(file_path, 'w') as file:
        file.write(paragraph)
