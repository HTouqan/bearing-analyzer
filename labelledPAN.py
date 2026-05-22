import onnxruntime
import cv2
from PIL import Image
import numpy as np
from torchvision import transforms
from PIL import Image
import os
import datetime
from pathlib import Path
lnum = 15




BASE_DIR = Path(__file__).parent
model_path = BASE_DIR.joinpath('model', 'mrcnn_bearing_gan.onnx')
crop_width = 580
crop_height = 1080
resize_width = 256
resize_height = 256




def to_numpy(tensor):
    return tensor.detach().cpu().numpy() if tensor.requires_grad else tensor.cpu().numpy()

def crop_and_resize_image_cv2(crop_width, crop_height, resize_width, resize_height, image_path):
    # Read the image
    img = cv2.imread(image_path)
    top= 280
    bottom = 70
        
    # If the image is grayscale, convert it to BGR
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    # Perform cropping 
    height, width , channel= img.shape
    x = int((width - crop_width) / 2)
    cropped_img = img[top:crop_height-bottom, x:x+crop_width]

    # Perform resizing
    resized_cropped_img = cv2.resize(cropped_img, (resize_width, resize_height))

    return resized_cropped_img

def crop_and_resize_image_cv2_img(crop_width, crop_height, resize_width, resize_height, imgM):

    img = imgM
    top= 280
    bottom = 70
    # If the image is grayscale, convert it to BGR
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    # Perform cropping
    height, width , channel= img.shape
    x = int((width - crop_width) / 2)
    cropped_img = img[top:crop_height-bottom, x:x+crop_width]

    # Perform resizing
    resized_cropped_img = cv2.resize(cropped_img, (resize_width, resize_height))

    return resized_cropped_img

def crop_and_resize_image_PIL(image_path, crop_width, crop_height, resize_width, resize_height):
    # Open the image file
    img = Image.open(image_path)

    # If the image is grayscale, convert it to RGB
    if img.mode != 'RGB':
        img = img.convert('RGB')
    top= 280
    bottom = 70
    # Perform cropping
    width, height = img.size
    left = int((width - crop_width) / 2)
    right = left + crop_width
    bottom = crop_height - bottom
    cropped_img = img.crop((left, top, right, bottom))

    # Perform resizing
    resized_cropped_img = cropped_img.resize((resize_width, resize_height))

    return resized_cropped_img

def transform_image(image, IMAGE_SIZE):
    transform_pipeline = transforms.Compose(
        [
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
        ]
    )
    return transform_pipeline(image).unsqueeze(0)
    
def log_message(message, printmessage, log_file_path = BASE_DIR.joinpath("logs.txt")):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    if printmessage == True:
        print(log_entry)
    with open(log_file_path, "a") as file:
        file.write(log_entry + "\n")   
     
def get_prediction(model_path, image):
    # Load an image

    preprocessed_image = image

    # Convert the image to a PyTorch tensor
    #transform = transforms.ToTensor()
    image_tensor = transform_image(preprocessed_image, 256)

    # Classifier for model selection
    model='bearing'
    models = {
        'chip': 'mrcnn_chip_gan.onnx',
        'bearing': 'mrcnn_bearing.onnx'
    }
    sess_options = onnxruntime.SessionOptions()
    sess_options.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_DISABLE_ALL
    ort_session = onnxruntime.InferenceSession(str(model_path), sess_options=sess_options)
    ort_inputs = {ort_session.get_inputs()[0].name: to_numpy(image_tensor)}
    ort_outs = ort_session.run(None, ort_inputs)
    
    results = {
        'boxes': ort_outs[0].tolist(),
        'labels': ort_outs[1].tolist(),
        'scores': ort_outs[2].tolist(),
        'masks': ort_outs[3].tolist()
    }
    return ort_outs

def view(image, output, counter, dir):
    # Convert the image to a numpy array
    image = np.array(image)
    # Convert the numpy array to a PIL Image object
    image = Image.fromarray(image).convert("RGBA")
    masks = output[-1]

    if len(masks) > 0:

        # RESIZE SOURCE IMAGE TO MASK SIZE
        mask_image = image.resize((256,256)).convert("RGBA")
        threshold = 0.01
        binary_masks = (masks > threshold).astype(int)
        
        # Sum along the first axis to merge the masks
        merged_mask = np.sum(binary_masks, axis=0)  # This creates a merged mask where 1 represents the presence of any mask
        merged_mask[0]=merged_mask[0]*255
        expanded_array = np.broadcast_to(merged_mask, (3, 256, 256))

        masks = Image.fromarray((expanded_array).astype(np.uint8).transpose(1, 2, 0))

        ### FEED THIS CONSOLIDATED MASK INTO A CALCULATION OF AREA
        width = masks.size[1]
        height = masks.size[1]
        
        for i in range(0, width):  # process all pixels
            for j in range(0, height):
                data = masks.getpixel((i, j))
                if data[:3] == (255,255,255):
                    masks.putpixel((i, j), (0, 191, 255, 125))
                else:
                    masks.putpixel((i, j), (0, 0, 0, 0))

        mask_image = mask_image.convert('RGBA')
        masks = masks.convert('RGBA')
        #masks.show()
        output_filename = os.path.join(dir, f'Mask_{counter}.jpg')
        Mask_np = np.array(masks)
        cv2.imwrite(output_filename, Mask_np)
        overlay = Image.blend(mask_image, masks, alpha=0.3)
        log_message(printmessage = False ,message = f'Img {counter+1}: mask generated and overlayed')
        return overlay
    else:
        log_message(printmessage = False ,message = f'Img {counter+1}: no mask found so an empty mask was overlayed')
        # Create an empty mask of the correct size
        empty_mask_np = np.zeros((256, 256), dtype=np.uint8)
        # Convert the empty mask to an Image object
        empty_mask = Image.fromarray(empty_mask_np)
        empty_mask = empty_mask.convert('RGBA')
        # Overlay the empty mask on the image
        overlay = Image.blend(image.convert('RGBA'), empty_mask, alpha=0.3)
        # Save the empty mask to a file
        output_filename = os.path.join(dir, f'Mask_{counter}.jpg')
        cv2.imwrite(output_filename, empty_mask_np)
        return overlay
        
def create_panorama_labelled(dir):
    # Load the resized images
    images = []
    for i in range(lnum):
        filename = os.path.join(dir, f'Labelled_image_{i}.jpg')
        img = cv2.imread(filename)
        images.append(img)

    # Combine the images to form a panoramic picture
    panorama = np.concatenate(images, axis=1)

    # Return the panoramic picture
    return panorama

def calculate_defect_percentage(mask):
    # Binarize the mask
    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    # Count the white pixels
    white_pixels = np.sum(mask == 255)

    # Calculate the total number of pixels
    total_pixels = np.prod(mask.shape)

    # Calculate the percentage of defect
    percent_defect = (white_pixels / total_pixels) * 100

    return percent_defect

def create_mask_panorama(dir):
    # Load the mask images
    masks = []
    for i in range(lnum):
        filename = os.path.join(dir, f'Mask_{i}.jpg')
        mask = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
        if mask is None or mask.ndim != 2:
            log_message(printmessage = False ,message = f'Img {i}:no mask available ')
            # Create a placeholder image of the correct size
            if masks:
                # Use the size of the previous mask
                height, width = masks[-1].shape
            else:
                # Default size if no masks have been loaded yet
                height, width = 256, 256  # Replace with the correct size
            mask = np.zeros((height, width), dtype=np.uint8)
        masks.append(mask)

    # Combine the masks to form a panoramic mask
    panorama_mask = np.concatenate(masks, axis=1)

    # Return the panoramic mask
    return panorama_mask

def create_panorama(dir):
    # Load the resized images
    images = []
    for i in range(lnum):
        filename = os.path.join(dir, f'Cropped_resized_image_{i}.jpg')
        img = cv2.imread(filename)
        
        # Check if the image was loaded correctly
        if img is None:
            log_message(printmessage = False ,message = f'Could not load image {filename}')
            continue
        
        # Check if the image has the correct dimensions
        if img.shape != (256, 256, 3):  # Replace height and width with the correct values
            log_message(printmessage = False ,message = f'Image {filename} has incorrect dimensions: {img.shape}')
            continue
        
        images.append(img)

    # Combine the images to form a panoramic picture
    panorama = np.concatenate(images, axis=1)

    # Return the panoramic picture
    return panorama

def get_next_instance_number(file_path):
    #Reads the current instance number from a file, increments it, and saves it back.
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            content = file.read().strip()
            instance_number = int(content) if content else 1
    else:
        instance_number = 1  # Start with 1 if file does not exist

    with open(file_path, 'w') as file:
        file.write(str(instance_number))

    return instance_number

def compare_images(image_path1, image_path2):
    # Load images
    img1 = cv2.imread(image_path1)
    img2 = cv2.imread(image_path2)
    
    # Check for equality
    if img1.shape == img2.shape and not(np.bitwise_xor(img1,img2).any()):
        return True  # Images are identical
    else:
        return False  # Images are different

def my_function(save_dir, callback1=None, callback2=None, *args):
    dir = Path(save_dir)

    Cap_img_dir = dir.joinpath('Original')
    output_dir_crop_resize = dir.joinpath('Processed')
    output_dir_labelled = dir.joinpath('Labelled')
    output_dir_Masks = dir.joinpath('Masks')
    Pan_Notlabeled = dir
    Pan_labeled = dir
    Pan_Mask = dir
    
    # Create directories if they don't exist
    for dir_path in [Cap_img_dir, output_dir_crop_resize, output_dir_labelled, output_dir_Masks]:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
    
    # Compare first and eighth images to check if the motor moved the part
    first_image_path = os.path.join(Cap_img_dir, "image_0.jpg")
    eighth_image_path = os.path.join(Cap_img_dir, "image_7.jpg")

    # Ensure both images exist before comparing
    if compare_images(first_image_path, eighth_image_path):
        log_message(printmessage = False ,message = f"Images are identical, motor did not move. Process halted.")
        return 'NOT_READY'
    else:
        log_message(printmessage = False ,message = f"Images are different, proceeding.")

    
    # Continue with the rest of the function if images are different
    for i in range(lnum):
        image_path = os.path.join(Cap_img_dir, f'image_{i}.jpg')
        preprocessed_image = crop_and_resize_image_PIL(image_path, crop_width, crop_height, resize_width, resize_height)
        output_filename = os.path.join(output_dir_crop_resize, f'Cropped_resized_image_{i}.jpg')
        preprocessed_image_np = np.array(preprocessed_image)
        cv2.imwrite(output_filename, preprocessed_image_np)
        results = get_prediction(model_path, preprocessed_image)
        Labeled_image = view(preprocessed_image, results, i, dir = output_dir_Masks)
        Labeled_image_np = np.array(Labeled_image)
        if callback1 is not None:
            callback1(Labeled_image_np, i)
        output_filename = str(output_dir_labelled.joinpath(f'Labelled_image_{i}.jpg'))
        cv2.imwrite(output_filename, Labeled_image_np)

    

    panorama = create_panorama(output_dir_crop_resize)
    cv2.imwrite(os.path.join(Pan_Notlabeled, 'panorama_NOlabel.jpg'), panorama)

    panorama = create_panorama_labelled(output_dir_labelled)
    cv2.imwrite(os.path.join(Pan_labeled, 'panorama_labelled.jpg'), panorama)
    
    panorama = create_mask_panorama(output_dir_Masks)
    cv2.imwrite(os.path.join(Pan_Mask, 'panorama_Mask.jpg'), panorama)

    # Load the panoramas
    panorama1 = cv2.imread(os.path.join(Pan_Notlabeled, 'panorama_NOlabel.jpg'))
    panorama2 = cv2.imread(os.path.join(Pan_labeled, 'panorama_labelled.jpg'))
    panorama3 = cv2.imread(os.path.join(Pan_Mask, 'panorama_Mask.jpg'))

    # Calculate the total height and maximum width
    space_height = 50
    total_height = panorama1.shape[0] + panorama2.shape[0] + panorama3.shape[0] + 300
    max_width = max(panorama1.shape[1], panorama2.shape[1], panorama3.shape[1])

    # Define the color of the space or line
    space_color = (0, 0, 255)  # Red color in BGR

    # Create a new image that is tall enough to hold all panoramas and spaces
    combined = np.zeros((total_height, max_width, 3), dtype=np.uint8)

    # Copy the panoramas into the new image
    combined[0:panorama1.shape[0], 0:panorama1.shape[1]] = panorama1
    combined[panorama1.shape[0]+space_height:panorama1.shape[0]+space_height+panorama2.shape[0], 0:panorama2.shape[1]] = panorama2
    combined[panorama1.shape[0]+space_height+panorama2.shape[0]+2*space_height:panorama1.shape[0]+space_height+panorama2.shape[0]+2*space_height+panorama3.shape[0], 0:panorama3.shape[1]] = panorama3

    # Fill the space with the specified color
    combined[panorama1.shape[0]:panorama1.shape[0]+space_height, :] = space_color
    combined[panorama1.shape[0]+space_height+panorama2.shape[0]:panorama1.shape[0]+space_height+panorama2.shape[0]+space_height, :] = space_color

    
    # Calculate the defect percentage for the panorama mask
    defect_percentage = calculate_defect_percentage(panorama3)
    defect_percentage = round(defect_percentage, 3)  # Round to 3 decimal places
    if callback2 is not None:
        callback2(defect_percentage)
    log_message(printmessage = False ,message = f"Defect percentage for panorama: {defect_percentage}%")

    # Convert the defect percentage to a string
    defect_percentage_str = f'Defect percentage: {defect_percentage}%'

    # Calculate the position for the text
    text_scale = 5 # Adjust as needed
    text_thickness = 5  # Adjust as needed
    text_size, _ = cv2.getTextSize(defect_percentage_str, cv2.FONT_HERSHEY_SIMPLEX, text_scale, text_thickness)
    text_x = (combined.shape[1] - text_size[0]) // 2
    text_y = combined.shape[0] - 50  # 50 pixels from the bottom

    # Add the text to the image
    cv2.putText(combined, defect_percentage_str, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, text_scale, (0, 0, 255), text_thickness)

    # Save the combined image
    cv2.imwrite(os.path.join(save_dir, 'combined_panorama.jpg'), combined)
    log_message(printmessage = True ,message = f"created combined_panorama.jpg")
    return 'DONE'
    
# Execute the main function, this way you can import this script without executing it
if __name__ == "__main__":        
    my_function()
