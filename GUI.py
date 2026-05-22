import tkinter as tk
from tkinter import ttk
from tkinter import  messagebox, simpledialog
from PIL import ImageTk, Image
from pypylon import pylon
import serial
import os, shutil
import threading
import time
import CamMotor3
import labelledPAN
import time
import datetime
import pathlib 

#__________________________________________________GLOBAL VARIABLES___________________________________________________________
# Get the directory of the current script
Program_Dir = os.path.dirname(os.path.realpath(__file__))

# Global flag to track the thread's running state
is_script1_running = False
is_script2_running = False

original_image = ''

# Set DirMAIN relative to the current script location
DirMAIN = os.path.join(Program_Dir, "Bearings")  # Adjust "Bearings" if it's in a different relative path
if not os.path.exists(DirMAIN):
    os.makedirs(DirMAIN)
# Logs_file initialization corrected
Logs_file = os.path.join(Program_Dir, "logs.txt")
# Create the log file if it doesn't exist (open in append mode then close immediately)
with open(Logs_file, 'a') as file:
    pass  # 'pass' does nothing, effectively just opening and closing the file
Assets_Dir = os.path.join(Program_Dir, "Assets")  
Active_Dir = ''
model_done_label = None

#__________________________________________________FUNCTIONS___________________________________________________________


# --------------------------------------------------------

    
def append_message(message, message_type="Info"):
    global Active_Dir
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"{current_time} -{message_type}: {message}"
    message_area.configure(state='normal')  # Enable text widget to modify its content
    message_area.insert(tk.END, f"{formatted_message}\n")  # Append message
    message_area.configure(state='disabled')  # Disable text widget to prevent user editing
    message_area.see(tk.END)  # Scroll to the end to show latest message
    log_message(printmessage = False ,message = formatted_message)

# --------------------------------------------------------
def log_message(message, printmessage, log_file_path = Logs_file):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    if printmessage == True:
        print(log_entry)
    with open(log_file_path, "a") as file:
        file.write(log_entry + "\n")
 
# --------------------------------------------------------
   
def on_model_finish():
    global Active_Dir
    combined_panorama_path = os.path.join(Active_Dir, 'combined_panorama.jpg')
    while not os.path.exists(combined_panorama_path):
        time.sleep(0.1)
    display_panoramic_image(combined_panorama_path[:-4])  # Assuming you want to remove '.jpg' for some reason


# --------------------------------------------------------
   
def show_current_panoramic_image():
    if Active_Dir:
        panoramic_image_path = os.path.join(Active_Dir, "combined_panorama.jpg")
        display_panoramic_image(panoramic_image_path)
    else:
        messagebox.showerror("Error", "No active directory selected or no panoramic image available.")

# --------------------------------------------------------
   
def list_directories(base_path):
    """List all directories in the given base path."""
    return [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]

# --------------------------------------------------------

def confirm_Active_Dir():
    global Active_Dir
    global model_done_label
    # Reset UI elements and variables
    clear_image_container()  # Clear the image display containers
    clear_model_image_container()

    # Reset progress bars
    progress_bar1['value'] = 0
    progress_var1.set(0)
    progress_bar1.update()

    progress_bar2['value'] = 0
    progress_var2.set(0)
    progress_bar2.update()

    # Hide or remove the "Model Done" label if it exists
    # Assuming `model_done_label` is globally accessible
    
    if 'model_done_label' in globals() and model_done_label is not None:
        model_done_label.destroy()  # Use this if you want to destroy the widget instead

    # Clear the image list
    image_listbox.delete(0, tk.END)

    # Refresh the directory dropdown and reset the active directory
    refresh_dropdown_menu()
    chosen_dir = dir_combobox.get()
    if chosen_dir:
        Active_Dir = os.path.join(DirMAIN, chosen_dir)
        active_dir_label.config(text=f"Active Directory: {Active_Dir}")
    else:
        messagebox.showerror("Error", "Please select a directory.")
        Active_Dir = ''  # Reset the active directory
        active_dir_label.config(text="Active Directory: Not selected")

# --------------------------------------------------------
 
def toggle_fullscreen(event=None):
    window.attributes('-fullscreen', not window.attributes('-fullscreen'))
    return "break"

# --------------------------------------------------------
 
def end_fullscreen(event=None):
    window.attributes('-fullscreen', False)
    return "break"

# --------------------------------------------------------
 
def on_directory_select(event):
    # This function can be used to update UI elements or perform actions
    # immediately after a directory is selected from the dropdown, before
    # clicking the confirm button.
    pass

# --------------------------------------------------------
 
def refresh_dropdown_menu(event=None):
    global DirMAIN
    dir_combobox['values'] = list_directories(DirMAIN)

# --------------------------------------------------------
 
def open_create_dir_dialog():
    CreateDirDialog(window)

# --------------------------------------------------------
 
def update_defect_label(percentage):
    defect_label.config(text="Defect Percentage: " + str(percentage))

# --------------------------------------------------------
    
def reset_and_delete_directories():
    # Use the user's home directory to construct the base path
    base_path = Path.home().joinpath("Bearings")
    
    # Ask for user confirmation
    confirm = messagebox.askyesno("Confirm Reset", "Are you sure you want to delete all directories and their subdirectories? This action cannot be undone.")
    if confirm:
        try:
            # Iterate through each item in the base directory
            for item in base_path.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
            append_message("All directories and their subdirectories have been deleted successfully.", "Reset Successful")
            
            # Reset the active directory as no directories exist anymore
            global Active_Dir
            Active_Dir = ''
           
            active_dir_label.config(text="Active Directory: Not selected")
            dir_combobox.set('')  # Clear the combobox selection
            
            # Refresh the directory list,
            refresh_dropdown_menu()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset: {e}")
    else:
        append_message("Reset operation has been cancelled.", "Reset Cancelled")
# --------------------------------------------------------
        
def delete_Active_Dir():
    global Active_Dir
    global DirMAIN
    if not Active_Dir:
        append_message("No active directory is currently selected.", "Error")
        return
    
    # Ask for user confirmation
    confirm = messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete the active directory? This action cannot be undone.")
    if confirm:
        try:
            if os.path.isdir(Active_Dir):
                shutil.rmtree(Active_Dir)
                append_message("The active directory has been deleted.", "Deletion Successful")
                Active_Dir = None  # Reset active directory to None or empty string
                active_dir_label.config(text="Active Directory: Not selected")  # Update the label to reflect the change
                dir_combobox.set('')  # Reset the combobox selection
                refresh_dropdown_menu()  # Refresh the dropdown menu to remove the deleted directory
            else:
                append_message("Active directory does not exist.", "Error")
        except Exception as e:
            append_message(f"Failed to delete the active directory: {e}", "Error")
    else:
        append_message("Active directory deletion has been cancelled.", "Deletion Cancelled")

# --------------------------------------------------------
 
class CreateDirDialog:
    def __init__(self, parent):
        self.parent = parent
        self.top = tk.Toplevel(parent)
        self.top.title("Create New Directory")
        # Initialize the entry widget for directory name input
        self.dir_name_entry = tk.Entry(self.top)
        self.dir_name_entry.pack()
        # Initialize the button to trigger create_directory method
        create_button = tk.Button(self.top, text="Create", command=self.create_directory)
        create_button.pack()
        # Rest of the initialization code

    def create_directory(self):
        dir_name = self.dir_name_entry.get()
        if dir_name:
            # Define the base directory dynamically based on the user's home directory
            base_dir = Path.home().joinpath("Bearings")
            # Ensure the base directory exists
            base_dir.mkdir(parents=True, exist_ok=True)
            # Construct the full path for the new directory
            new_dir_path = base_dir.joinpath(dir_name)
            # Create the new directory
            try:
                new_dir_path.mkdir(exist_ok=False)  # exist_ok=False will raise an error if the directory already exists
                append_message(f"Directory '{dir_name}' created successfully.", "Success")
            except FileExistsError:
                append_message(f"Directory '{dir_name}' already exists.", "Error")
        else:
            append_message("Directory name cannot be empty.", "Error")

# --------------------------------------------------------
 
def create_new_directory(base_path, dir_name):
    new_dir_path = os.path.join(base_path, dir_name)
    try:
        os.makedirs(new_dir_path, exist_ok=False)
        # Create predefined subdirectories
        for sub_dir in ["Original", "Masks", "Labelled", "Processed"]:
            os.makedirs(os.path.join(new_dir_path, sub_dir), exist_ok=True)
        append_message("Directory and subdirectories created successfully.", "Success")
        refresh_dropdown_menu()  # Assuming this updates some UI element to reflect the change
    except FileExistsError:
        append_message("Directory already exists. Please choose a different name.", "Error")
    except Exception as e:
        append_message(f"Failed to create directory: {e}", "Error")

# --------------------------------------------------------
 
def run_script1():
    global is_script1_running

    # Check if the script is already running
    if is_script1_running:
        append_message("Image capture is already running. Please wait.", "warning")
        return

    append_message("Image capture is running now...", "info")
    # Reset the progress bar
    progress_bar1['value'] = 0
    progress_bar1.update()

    # Mark Image capture as running
    is_script1_running = True

    def wrapper_run_image_capture():
        try:
            run_image_capture()
        finally:
            global is_script1_running
            is_script1_running = False

    # Start the thread
    capture_thread = threading.Thread(target=wrapper_run_image_capture)
    capture_thread.start()


# --------------------------------------------------------
    
def display_panoramic_image(image_path):
    if not os.path.exists(image_path):
        messagebox.showinfo("Image Not Found", "The image file does not exist. It will be generated at the end of the model run.")
        return
    # Create a top-level window for the popup
    popup = tk.Toplevel(window)
    popup.title("Analysis Result")

    # Open the image using PIL
    image = Image.open(image_path)

    # Resize the image if needed (optional, depending on desired size)
    image = image.resize((2500, 1280), Image.Resampling.LANCZOS)


    # Convert the PIL image to a PhotoImage object
    tk_image = ImageTk.PhotoImage(image)

    # Create a label in the popup window and set the image
    image_label = tk.Label(popup, image=tk_image)
    image_label.image = tk_image  # Keep a reference to the image object
    image_label.pack()

    # Create a button in the popup window to close it
    close_button = tk.Button(popup, text="Close", command=popup.destroy)
    close_button.pack()
# --------------------------------------------------------
     
def run_script2():
    global is_script2_running

    # Check if the script is already running
    if is_script2_running:
        append_message("Model Analysis is already running. Please wait.", "warning")
        return

    append_message("Model Analysis is running now...", "info")
    # Reset the progress bar
    progress_bar2['value'] = 0
    progress_bar2.update()

    # Mark script 2 as running
    is_script2_running = True

    def wrapper_run_model():
        try:
            run_model()
        finally:
            global is_script2_running
            is_script2_running = False

    # Start the thread
    model_thread = threading.Thread(target=wrapper_run_model)
    model_thread.start()


# --------------------------------------------------------
 
def run_entire_process():
    global Active_Dir
    new_dir_name = simpledialog.askstring("New Directory", "Enter the name for the new directory:")
    if not new_dir_name or new_dir_name.strip() == "":
        append_message("No directory name was provided. Operation cancelled.", "Warning")
        return

    create_new_directory(DirMAIN, new_dir_name)
    Active_Dir = os.path.join(DirMAIN, new_dir_name)
    active_dir_label.config(text=f"Active Directory: {Active_Dir}")
    progress_bar2['value'] = 0
    progress_var2.set(0)
    progress_bar2.update()
    def run_process():
        result = run_image_capture()
        if result == 'DONE':
            append_message("Inputing imgs into Model now.", "Info")
            run_model()
            append_message("Model Done", "Success")

    global capture_thread
    capture_thread = threading.Thread(target=run_process)
    capture_thread.start()

# --------------------------------------------------------
     
def update_image_list():
    global DirMAIN, Active_Dir
    if not Active_Dir or Active_Dir.strip() == "":
        append_message("Active directory is not set.", "Error")
        return
    
    Img_Dir = os.path.join(Active_Dir, "Original")
    image_files = [file for file in os.listdir(Img_Dir) if file.endswith('.jpg')]

    
    if not image_files:
        append_message("No images found. Please run the image capture function.", "Info")
        return

    # Clear the listbox
    image_listbox.delete(0, tk.END)
    
    # custom sorting function that sorts the images based on the number after the underscore
    def sort_images(image):
        number = int(image.split('_')[1].split('.')[0])
        return number

    # Sort the list of image files using the custom sorting function
    image_files = sorted(image_files, key=sort_images)

    # Add image file names to the listbox
    for file in image_files:
        image_listbox.insert(tk.END, file)

# --------------------------------------------------------
 
def show_selected_image(event):
    global Active_Dir

    # Check if there is a selection
    selection = image_listbox.curselection()
    if not selection:  # If selection is empty, do nothing
        return

    # Proceed if there is a selection
    selected_index = selection[0]  # Assuming you want the first item if multiple are selected
    selected_image = image_listbox.get(selected_index)

    Img_Dir = os.path.join(Active_Dir, "Original")
    image_path = os.path.join(Img_Dir, selected_image)
    
    # Open and display the selected image
    try:
        image = Image.open(image_path)
        image = image.resize((300, 300))  # Adjust the size as needed
        photo = ImageTk.PhotoImage(image)
        image_label.configure(image=photo)
        image_label.image = photo  # Keep a reference
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open image: {e}")


# --------------------------------------------------------
 
def clear_image_container():
    for widget in image_container.scrollable_frame.winfo_children():
        widget.destroy()

# --------------------------------------------------------
 
class ScrollableFrame(tk.Frame):
    def __init__(self, container, border_color='black', border_width=2, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=border_width, highlightbackground=border_color)
        self.scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.scrollable_frame = tk.Frame(self.canvas)
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(xscrollcommand=self.scrollbar.set)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        self.canvas.pack(side="top", fill="both", expand=True)
        self.scrollbar.pack(side="bottom", fill="x")


# --------------------------------------------------------
 
def run_image_capture():
    global capture_thread
    global Active_Dir
    if not Active_Dir:
        append_message("Please select an active directory first.", "Error")
        return
   
    clear_image_container()
    clear_model_image_container()
    try:
        # Initialize serial connection
        ser = serial.Serial('COM4', 9600)
        CamMotor3.StealthchopON(ser)   
    except Exception as e:
        # Append the error message
        append_message(f'This exception most likely means the port for the motor is incorrect [{str(e)}]', "Error")

        # Exit the function
        return
    
    try:
        # Setup camera
        camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
    except Exception as e:
        # Append the error message
        append_message(f'This exception most likely means the camera is not connected [{str(e)}]', "Error")

        # Exit the function
        return

    camera.Open()
    camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
    converter = pylon.ImageFormatConverter()
    converter.OutputPixelFormat = pylon.PixelType_BGR8packed
    converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
    
    # Prepare for capturing
    image_counter = 0
    max_images = 15
    progress_bar1['value'] = 0
    progress_var1.set(0)
    progress_bar1.update()

    # Perform the image capture
    result = CamMotor3.capture_and_save_images(ser, Active_Dir, image_counter, max_images, converter, camera, callback=update_label)

    # Check the execution time
   
    if result == 'FAILED':
        # Notify the user in the main thread if the process was too quick
        window.after(0, lambda: append_message("The motor is not being powered", "Error"))
        
        # Clear the image container
        clear_image_container()
        clear_model_image_container()
        # Delete all captured images
        for i in range(image_counter):
            image_filename = f"image_{i}.jpg" 
            image_path = os.path.join(Active_Dir, "Original", image_filename)  
            if os.path.exists(image_path):
                os.remove(image_path)
        # Reset the progress bar
        progress_bar1['value'] = 0
        progress_var1.set(0)
        progress_bar1.update()
    else:
        if result == 'DONE':
            # Handle the case when all images have been captured
            print('All images have been captured.')
            window.after(0, lambda: append_message("All images have been successfully captured.", "Success"))
    
    return result

# --------------------------------------------------------
     
def update_label(image, i):
    # Define the crop and resize dimensions
    crop_width = 580
    crop_height = 1080
    resize_width = 256
    resize_height = 256

    # Crop and resize the image
    cropped_image = labelledPAN.crop_and_resize_image_cv2_img(crop_width, crop_height, resize_width, resize_height, image)

    # Convert the cropped image to a format that can be used with Tkinter
    img = Image.fromarray(cropped_image)
    img.thumbnail((250, 250))  # Resize the image to 200x200
    photo = ImageTk.PhotoImage(img)

    # Display the cropped image
    label = tk.Label(image_container.scrollable_frame, image=photo)
    label.image = photo  # Keep a reference
    label.pack(side="left")  # Add padding between images

    # Update the progress bar
    progress_var1.set(i)
    progress_bar1['value'] = i 
    progress_bar1.update()

# --------------------------------------------------------
 
def run_model():
    global Active_Dir
    global model_done_label
    global model_done_label
    
    if 'model_done_label' in globals() and model_done_label is not None:
        model_done_label.destroy()  # Use this if you want to destroy the widget instead
    if not Active_Dir:
        append_message("Please select an active directory first.", "Error")
        return
    original_dir_path = os.path.join(Active_Dir, 'Original')
    image_files = os.listdir(original_dir_path)
    if len(image_files) < 15:
        append_message("There is not enough captured images to run the model. Please run image capture again.", "Error")
        return
    
    # Call the function that runs the model and generates the panoramic image
    result = labelledPAN.my_function(Active_Dir, callback1=update_model_label, callback2=update_defect_label)
    if result == 'NOT READY':
        append_message("Images are identical, The motor is not powered", "Info")
        return 
        
    # Wait for the panoramic image to be created in a separate thread
    def wait_for_image_and_display():
        panorama_image_path = os.path.join(Active_Dir, "combined_panorama.jpg")
        while not os.path.exists(panorama_image_path):
            time.sleep(0.1)  # Wait a little before checking again
        window.after(0, lambda: display_panoramic_image(panorama_image_path))

    threading.Thread(target=wait_for_image_and_display).start()
    
    if model_done_label is not None:
        model_done_label.destroy()  # Destroy the previous instance before creating a new one

    model_done_label = tk.Label(frameDIR, text="Model Done")
    model_done_label.grid(row=0, column=5, padx=10)
   
# --------------------------------------------------------
        
def update_model_label(processed_image,i):
    global Active_Dir
    if not Active_Dir:
        append_message("Please select an active directory first.", "Error")
        return
    # Convert the processed image to a format that can be used with Tkinter
    img = Image.fromarray(processed_image)
    img.thumbnail((250, 250))  # Resize the image to 200x200
    photo = ImageTk.PhotoImage(img)

    # Display the processed image
    label = tk.Label(model_image_container.scrollable_frame, image=photo)
    label.image = photo  # Keep a reference
    label.pack(side="left")
    
    # Update the progress bar
    i += 1
    progress_var2.set(i)
    progress_bar2['value'] = i 
    progress_bar2.update()

# --------------------------------------------------------
   
def clear_model_image_container():
    for widget in model_image_container.scrollable_frame.winfo_children():
        widget.destroy()

# _______________________________________________MAIN WIDGET_____________________________________________________

window = tk.Tk()
window.title("Bearing Rating")

# Configure the grid to expand
window.rowconfigure(0, weight=1)
window.rowconfigure(1, weight=1)
window.rowconfigure(4, weight=1)
window.rowconfigure(5, weight=1)
window.rowconfigure(6, weight=1)
window.columnconfigure(0, weight=1)
window.columnconfigure(1, weight=1)

window.resizable(True, True)

window.attributes('-fullscreen', True)
window.bind('<F11>', toggle_fullscreen)
window.bind('<Escape>', end_fullscreen)
#_____________________________________________MAIN WIDGET VAR_____________________________________________________

empty_image = Image.new('RGB', (300, 300), 'white')  # Change the size as needed
empty_photo = ImageTk.PhotoImage(empty_image)

#  Load and resize images
# NOTE: replace Logo.png in ./Assets with your own logo (250x129 px recommended).
# The original branded asset has been removed for this public release.
_logo_path = os.path.join(Assets_Dir, "Logo.png")
if os.path.exists(_logo_path):
    image2 = Image.open(_logo_path).resize((250, 129), Image.LANCZOS)
else:
    image2 = Image.new('RGB', (250, 129), 'white')
image3 = Image.open(os.path.join(Assets_Dir, "Run_icon.png")).resize((50, 50), Image.LANCZOS)


# Convert the PIL image objects to Tkinter PhotoImage objects
logo_image = ImageTk.PhotoImage(image2)
icon_image = ImageTk.PhotoImage(image3)

progress_var1 = tk.IntVar()
progress_var2 = tk.IntVar()
#__________________________________________________FRAMES________________________________________________________

frameDIR = tk.Frame(window, pady=10)
frameDIR.grid(row=0, column=0, columnspan=2, sticky="nsew")
frameDIR.columnconfigure((0,1,5,6,7,8), weight=1)  # Configure columns within frameDIR for equal distribution

logo_label = tk.Label(frameDIR, image=logo_image)
logo_label.grid(row=0, column=8, sticky="ew")

frame1 = tk.Frame(window)
frame1.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

frame2 = tk.Frame(window)
frame2.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)

frame3 = tk.Frame(window)
frame3.grid(row=4, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

frame4 = tk.Frame(window)
frame4.grid(row=5, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

# Configure frames for expansion
for i in range(1):  # Adjust as needed for the number of columns in your frames
    frame1.columnconfigure(i, weight=1)
    frame2.columnconfigure(i, weight=1)
    frame3.columnconfigure(i, weight=1)
    frame4.columnconfigure(i, weight=1)

frame1.rowconfigure(0, weight=1)
frame2.rowconfigure(0, weight=1)
frame3.rowconfigure(0, weight=1)
frame4.rowconfigure(0, weight=1)
frame3.rowconfigure(0, weight=1)
frame3.columnconfigure([0, 1], weight=1)

frame4.rowconfigure(0, weight=1)
frame4.columnconfigure([0, 1], weight=1)


#__________________________________________________BUTTONS___________________________________________________________
Button_height = 5
Button_width = 20

# Add the RUN button to your GUI, assuming it's placed in frame1 for consistency
run_all_button = tk.Button(frame1, image= icon_image, text= 'Run' , command=run_entire_process)
run_all_button.grid(row=0, column=0, padx=5, pady=5)

# Create a button to run the script
run_button = tk.Button(frame1, text="Run Image Capture", command=run_script1)
run_button.grid(row=0, column=1, padx=5, pady=5)

# Create a button to update the image list
update_button = tk.Button(frame2, text="Update Image List", command=update_image_list)
update_button.grid(row=0, column=0, padx=5, pady=5)

model_button = tk.Button(frame1, text="Run Model", command=run_script2)
model_button.grid(row=0, column=2, padx=5, pady=5)

confirm_button = tk.Button(frameDIR, text="Confirm", command=confirm_Active_Dir)
confirm_button.grid(row=0, column=1, sticky="nsew", padx=10)

create_dir_button = tk.Button(frame1, text="Create New Directory", command=open_create_dir_dialog)
create_dir_button.grid(row=0, column=3, padx=5, pady=5)

delete_active_dir_button = tk.Button(frame1, text="Delete Active Directory", command=delete_Active_Dir)
delete_active_dir_button.grid(row=0, column=4, padx=5, pady=5)

reset_button = tk.Button(frame1,text="Reset Directories", command=reset_and_delete_directories)
reset_button.grid(row=0, column=5, padx=5, pady=5)

show_panoramic_button = tk.Button(frameDIR, text="Show Panoramic Image", command=show_current_panoramic_image)
show_panoramic_button.grid(row=0, column=7, padx=10)


#_________________________________________________LABELS____________________________________________________________


active_dir_label = tk.Label(frameDIR, text="Active Directory: Not selected")
active_dir_label.grid(row=1, column=0, padx=10)

defect_label = tk.Label(frameDIR, text="Defect Percentage: Not Calculated yet")
defect_label.grid(row=0, column=6, padx=100, pady=10)

# Create the label with the empty image
image_label = tk.Label(frame2, image=empty_photo)
image_label.image = empty_photo  # Keep a reference
image_label.grid(row=0, column=2, sticky="nsew")


#________________________________________________WIDGETS_____________________________________________________________

# Create a combobox to select the active directory
dir_combobox = ttk.Combobox(frameDIR, width=50, state="readonly")
dir_combobox['values'] = list_directories(DirMAIN)
dir_combobox.grid(row=0, column=0)
dir_combobox.bind("<<ComboboxSelected>>", on_directory_select)

# Create a listbox to display the image file names
image_listbox = tk.Listbox(frame2)
image_listbox.grid(row=0, column=1)
image_listbox.bind('<<ListboxSelect>>', show_selected_image)

# Create a non-scrollable frame to display the images
image_container = ScrollableFrame(frame3)
image_container.grid(row=0, column=0, columnspan=2, sticky="nsew")

model_image_container = ScrollableFrame(frame4)  # You can place it in a different frame if needed
model_image_container.grid(row=0, column=0, columnspan=2, sticky="nsew")

# Update the progress bar grid placement with columnspan and consistent sticky attribute
progress_bar1 = ttk.Progressbar(frame3, length=200, mode='determinate', maximum=15, variable=progress_var1)
progress_bar1.grid(row=1, column=0, columnspan=2, sticky="ew")  # Ensure it expands to fill the cell

progress_bar2 = ttk.Progressbar(frame4, length=200, mode='determinate', maximum=15, variable=progress_var2)
progress_bar2.grid(row=1, column=0, columnspan=2, sticky="ew")  # Ensure it expands to fill the cell

# Create a text area to display messages
message_area = tk.Text(window, height=10, width=50, state='disabled', bg='lightgrey')
message_area.grid(row=6, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")


window.mainloop()
