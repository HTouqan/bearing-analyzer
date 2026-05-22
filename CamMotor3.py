from pypylon import pylon
import cv2
import time
import serial
import os
import datetime
DirMAIN = os.path.dirname(os.path.realpath(__file__))

if not os.path.exists(DirMAIN):
    os.makedirs(DirMAIN)
Logs_file = DirMAIN + r"\logs.txt"

def StealthchopON(ser):
    Instruction_number = 0x05 # Instruction number for setting parameters
    # Set up the serial connection
    #_______________________________________________________________
    Target_address = 0x01
    Type = 4
    Motor = 0x00

    DF = create_data_frame(Target_address, Instruction_number, Type, Motor, 4999)
    
    ser.write(DF)
    #_______________________________________________________________ 
    Target_address = 0x01
    Type = 182
    Motor = 0x00

    DF = create_data_frame(Target_address, Instruction_number, Type, Motor, 5000)
    
    ser.write(DF)
    #_______________________________________________________________
    Target_address = 0x01
    Type = 186
    Motor = 0x00

    DF = create_data_frame(Target_address, Instruction_number, Type, Motor, 5000)
    
    ser.write(DF)
    #_______________________________________________________________
    Target_address = 0x01
    Type = 187
    Motor = 0x00
    Parametervalue = 15

    DF = create_data_frame(Target_address, Instruction_number, Type, Motor, Parametervalue)
    
    ser.write(DF)
    #_______________________________________________________________  
    print("---------------------------------------------------------------StealthChop mode is ON---------------------------------------------------------------")
    
# Function to create data frame
def create_data_frame(target_address, instruction_number, instruction_type, motor_id, pvalue):
    # Create the data frame
    data_frame = bytearray([target_address, instruction_number, instruction_type, motor_id])
    data_frame += pvalue.to_bytes(4, 'big')
    # Calculate the checksum
    checksum = sum(data_frame) % 256
    data_frame += checksum.to_bytes(1, 'big')
    return data_frame

def log_message(message, printmessage, log_file_path = Logs_file):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    if printmessage == True:
        print(log_entry)
    with open(log_file_path, "a") as file:
        file.write(log_entry + "\n")
        
        
def Check_Motor_flag(ser):
    ser.reset_input_buffer()
    DF = create_data_frame(0x01, 0x06, 0x08, 0x00, 1)
    ser.write(DF)
    binary_value = ser.read(9)
    # Extract the 8th element (index 7) directly
    flag = binary_value[7]

    return flag
        
        
# Function to send motor instruction
def send_motor_instruction(angle, ser):
    degrees = angle
    rfullstep = 200  # fullstep resolution of the motor (with most motors 200 (1.8°))
    rmicrostep = 256  # microstep setting of the module (default 256)
    steps = round(degrees / (360 / (rfullstep * rmicrostep)))
    # Create the data frame for the motor instruction
    target_address = 0x01
    instruction_number = 0x04
    instruction_type = 0x01
    motor_id = 0x00 
    data_frame = create_data_frame(target_address, instruction_number, instruction_type, motor_id, steps)
    # Send the motor instruction
    ser.write(data_frame)
    log_message(printmessage = False ,message = f"Motor instruction sent: {data_frame}")

def capture_and_save_images(ser, save_dir, image_counter, max_images, converter , camera, callback = None):
    # Ensure save_dir exists or create it
    os.makedirs(save_dir, exist_ok=True)
    # Use the provided directory for saving images
     
    start_time = time.time()
    while camera.IsGrabbing() and image_counter < max_images:
        # Send the motor instruction to move to a certain angle
        
        angle = 360 / max_images
        send_motor_instruction(angle,ser)
        # Wait for the motor to reach the desired position
        while Check_Motor_flag(ser) != 1:
            time.sleep(0.2)
        # Capture an image after the motor reaches the desired position
        grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
        if grab_result.GrabSucceeded() and image_counter <= max_images:
            # Save the current image to a file
            image = converter.Convert(grab_result)
            img = image.GetArray()
            # Flip the image
            img = cv2.flip(img, 1)
            filename = f'{save_dir}/Original/image_{image_counter}.jpg'
            print(filename)
            log_message(printmessage = True, message = f'Img {image_counter + 1}:Image Captured and successfully saved, filename: {filename}')
            cv2.imwrite(filename, img)
            image_counter += 1
            if callback is not None and image_counter <= max_images:
                
                callback(img, image_counter)
            
            # Display the current image
            #cv2.namedWindow('Basler Camera', cv2.WINDOW_NORMAL)
            #cv2.imshow('Basler Camera', img)
            k = cv2.waitKey(1)
            if k == 27:
                break
    end_time = time.time()
    total_time = end_time - start_time
    if total_time<10 :
        log_message(printmessage = True, message = f"image capturing failed, check Power to motor, or error in capturing images, TIME:{total_time}s")
        return 'FAILED'
    else:
        return 'DONE'


def my_function():
    ser = serial.Serial('COM4', 9600)
    start_time = time.time()

    StealthchopON(ser)

    # Create an instant camera object with the camera device found first.
    camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
    camera.Open()
    camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
    converter = pylon.ImageFormatConverter()
    converter.OutputPixelFormat = pylon.PixelType_BGR8packed
    converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
    image_counter = 0
    max_images = 15  # Set the maximum number of images to take
    save_dir = DirMAIN + r"\Bearings\testing"  # Set the directory for saving images
    capture_and_save_images(ser, save_dir, image_counter, max_images, converter, camera, callback = None)


    camera.StopGrabbing()
    camera.Close()
    cv2.destroyAllWindows()

    # Record the end time
    end_time = time.time()

    # Calculate and print the total execution time
    total_time = end_time - start_time
    if total_time<15 :
        log_message(printmessage = True, message = f"image capturing failed, check Power to motor, or error in capturing images, TIME:{total_time}s")
    else:
        log_message(printmessage = True, message = f"Capturing images, Total execution time: {total_time} seconds")
        log_message(printmessage = False, message = f"--END OF SCRIPT CamMotor3--")
    ser.close()


# Execute the main function, this way you can import this script without executing it
if __name__ == "__main__":        
    my_function()