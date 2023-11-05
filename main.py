
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

import requests
from PIL import Image, ImageFilter
import io
import numpy

#if token exists in token.txt, read it
try:
    with open('token.txt', 'r') as f:
        TOKEN = f.read().strip()
except FileNotFoundError:
    #ask user to input token
    TOKEN = input("Enter your bot's token: ")
    with open('token.txt', 'w') as f:
        f.write(TOKEN)

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(update.effective_user)
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')

def find_coeffs(pa, pb):
    matrix = []
    for p1, p2 in zip(pa, pb):
        matrix.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0]*p1[0], -p2[0]*p1[1]])
        matrix.append([0, 0, 0, p1[0], p1[1], 1, -p2[1]*p1[0], -p2[1]*p1[1]])

    A = numpy.matrix(matrix, dtype=numpy.float32)
    B = numpy.array(pb).reshape(8)

    res = numpy.dot(numpy.linalg.inv(A.T * A) * A.T, B)
    return numpy.array(res).reshape(8)
    
def image_process(image):
    background_image = Image.open('yigitlooks.jpg')
    background_image = background_image.convert('RGBA')
    
    image = image.filter(ImageFilter.GaussianBlur(radius=0.5))

    width, height = image.size
    aspect_ratio = 16 / 9

    # Determine the target height and width based on the image's aspect ratio
    if width / height > aspect_ratio:
        # Image is too wide
        new_height = height
        new_width = int(height * aspect_ratio)
    else:
        # Image is too tall
        new_width = width
        new_height = int(width / aspect_ratio)

    # Calculate cropping area
    left = (width - new_width) / 2
    top = (height - new_height) / 2
    right = (width + new_width) / 2
    bottom = (height + new_height) / 2
    crop_area = (left, top, right, bottom)

    # Crop the image to the 16:9 aspect ratio
    image = image.crop(crop_area)
    width, height = image.size

    size = 1024
    coeffs = find_coeffs(
        [(121, 177), (480, 254), (129, 518), (475, 502)],
        [(0, 0), (width, 0), (0, height), (width, height)]
        )

    # Resize the image to 512x512
    #image = image.resize((size, size), Image.BICUBIC)
    image_o = image.transform((size, size), Image.PERSPECTIVE, coeffs, Image.BICUBIC, fillcolor=(0, 0, 0, 0))
    
    mask = Image.new("L", (width, height), 255)
    mask = mask.transform((size, size), Image.PERSPECTIVE, coeffs, Image.BICUBIC, fillcolor=(0))


    #put image to background
    background_image.paste(image_o, (0, 0), mask)


    reflection_coeffs = find_coeffs(
        [(615, 279), (777, 315), (608, 494), (765, 481)],
        [(0, 0), (width, 0), (0, height), (width, height)]
        )

    image_reflection = image.transpose(Image.FLIP_LEFT_RIGHT)
    image_reflection = image_reflection.transform((size, size), Image.PERSPECTIVE, reflection_coeffs, Image.BICUBIC, fillcolor=(0, 0, 0, 0))

    #blur image
    image_reflection = image_reflection.filter(ImageFilter.GaussianBlur(radius=5))

    mask = Image.new("L", (width, height), 50)
    mask = mask.transform((size, size), Image.PERSPECTIVE, reflection_coeffs, Image.BICUBIC, fillcolor=(0))
    mask = mask.filter(ImageFilter.GaussianBlur(radius=5))

    #put image to background
    background_image.paste(image_reflection, (0, 0), mask)
    
    return background_image

async def process_image(update: Update, context: ContextTypes.DEFAULT_TYPE, photo) -> None:
    # Get the file_id
    file_id = photo.file_id

    # Get the file_path
    photo_file = await context.bot.get_file(file_id)
    
    # Download the photo via its file_path
    photo_bytes = await photo_file.download_as_bytearray()

    # Open the image using PIL
    image = Image.open(io.BytesIO(photo_bytes))
    image = image.convert('RGBA')

    processed_image = image_process(image)
    
    # Save the processed image to a byte array
    img_byte_arr = io.BytesIO()
    processed_image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    # Send the processed image back to the user
    await update.message.reply_photo(photo=img_byte_arr)

async def handle_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    #check if message contains @yigitlooks_bot
    caption_or_text = update.message.caption or update.message.text
    if caption_or_text:
        if '@yigitlooks_bot' in caption_or_text:
            if update.message.photo:
                photo = update.message.photo[-1]
                await process_image(update, context, photo)
            else:
                if update.message.reply_to_message:
                    if update.message.reply_to_message.photo:
                        photo = update.message.reply_to_message.photo[-1]
                        await process_image(update, context, photo)
                    else:
                        await update.message.reply_text('photo pls')
        

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters=filters.ALL, callback=handle_task))

app.run_polling()