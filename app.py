from flask import Flask, jsonify, request, render_template, redirect, url_for, Response
import torch
import cv2
import numpy as np
import os
import time
import base64 
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}
# Dynamic time configuration
MAX_AVAILABLE_TIME = 300   # maximum cap for cycle time (seconds)
BASE_TIME = 40             # minimum cycle time (seconds)
PER_VEHICLE_TIME = 4      # extra seconds added per detected vehicle

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global state variables
sides = ['b', 'c', 'd', 'e']
sides_status = {side: {
    'visited': False, 
    'incoming_vehicles': 0,
    'outgoing_vehicles': 0,
    'total_vehicles': 0
} for side in sides}
available_time = BASE_TIME   # initialized to minimum cycle time for UI before any upload

current_green = -1
signal_times = [0, 0, 0, 0]  # Time allocated for each side [b, c, d, e]
processing_complete = False

# Load YOLOv5 model (wrapped to avoid app crash if download fails)
vehicle_classes = [2, 3, 5, 7]  # COCO indices for car, truck, bus, motorcycle
try:
    # This downloads/loads the model the first time — requires internet
    model = torch.hub.load('ultralytics/yolov5', 'yolov5s', verbose=False)
except Exception as e:
    # If model fails to load, set model = None and continue so server doesn't crash
    model = None
    print("Warning: YOLOv5 model failed to load at startup. Detection will return 0. Error:", e)

def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def allowed_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

def detect_vehicles_in_image(image_path):
    """Count vehicles in an image using YOLOv5"""
    # If model failed to load, return 0 detections and avoid crashing
    if model is None:
        print("Debug: model is None — detect_vehicles_in_image returning 0")
        return 0

    results = model(image_path)
    ...
    
    # Filter results for vehicle classes only
    vehicles_detected = 0
    for detection in results.xyxy[0]:  # Process results
        class_id = int(detection[5])
        confidence = float(detection[4])
        if class_id in vehicle_classes and confidence > 0.5:  # Only count vehicles with confidence > 50%
            vehicles_detected += 1
            
    return vehicles_detected

def detect_vehicles_in_video(video_path):
    """Count vehicles in a video using YOLOv5"""
    cap = cv2.VideoCapture(video_path)
    
    # Sample frames at regular intervals
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = total_frames / fps
    
    # If video is longer than 20 seconds, sample every 2 seconds
    sample_interval = 2 if duration > 20 else 1
    sample_frame_interval = int(fps * sample_interval)
    
    max_vehicles = 0
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_count % sample_frame_interval == 0:
            # Save frame temporarily
            temp_frame_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_frame.jpg')
            cv2.imwrite(temp_frame_path, frame)
            
            # Detect vehicles in the frame
            vehicles = detect_vehicles_in_image(temp_frame_path)
            max_vehicles = max(max_vehicles, vehicles)
            
            # Remove temporary frame
            os.remove(temp_frame_path)
        
        frame_count += 1
    
    cap.release()
    return max_vehicles

def compute_dynamic_available_time():
    """Compute total available cycle time dynamically from detected vehicles."""
    total_vehicles_all = sum(sides_status[side]['total_vehicles'] for side in sides)
    dynamic_time = BASE_TIME + (total_vehicles_all * PER_VEHICLE_TIME)
    dynamic_time = min(dynamic_time, MAX_AVAILABLE_TIME)
    return dynamic_time

def reset_system():
    """Reset the system for a new cycle"""
    global sides_status, available_time, current_green, signal_times, processing_complete
    ...

    sides_status = {side: {
        'visited': False, 
        'incoming_vehicles': 0,
        'outgoing_vehicles': 0,
        'total_vehicles': 0
    } for side in sides}
    available_time = BASE_TIME   # initialized to minimum cycle time for UI before any upload
    current_green = -1
    signal_times = [0, 0, 0, 0]
    processing_complete = False

def calculate_signal_time():
    """Calculate signal time based on vehicle distribution"""
    global sides_status, available_time, current_green, signal_times, processing_complete
    
    # Get unvisited sides
    unvisited_sides = [side for side in sides if not sides_status[side]['visited']]
    
    if not unvisited_sides:
        # All sides visited, reset for next cycle
        reset_system()
        return
    
    # Calculate total vehicles in unvisited sides
    total_vehicles = sum(sides_status[side]['total_vehicles'] for side in unvisited_sides)
    
    if total_vehicles == 0:
        # No vehicles detected, distribute time equally
        allocated_time = available_time / len(unvisited_sides)
        for side in unvisited_sides:
            side_index = sides.index(side)
            signal_times[side_index] = allocated_time
        
        # Select the first unvisited side
        most_vehicles_side = unvisited_sides[0]
    else:
        # Find side with most vehicles
        most_vehicles_side = max(unvisited_sides, key=lambda side: sides_status[side]['total_vehicles'])
        
        # Calculate allocated time
        vehicles_on_side = sides_status[most_vehicles_side]['total_vehicles']
        allocated_time = int((vehicles_on_side * available_time) / total_vehicles)
    
    # Update system state
    sides_status[most_vehicles_side]['visited'] = True
    current_green = sides.index(most_vehicles_side)
    signal_times[current_green] = allocated_time
    available_time -= allocated_time
    processing_complete = True

@app.route('/')
def index():
    """Render the input selection form"""
    return render_template('index.html')

@app.route('/select_upload_method', methods=['POST'])
def select_upload_method():
    """Handle selection of upload method"""
    upload_method = request.form.get('upload_method')
    
    if upload_method == 'image':
        return redirect(url_for('image_upload_form'))
    elif upload_method == 'video':
        return redirect(url_for('video_upload_form'))
    elif upload_method == 'webcam_image':
        return redirect(url_for('webcam_image_capture'))
    elif upload_method == 'webcam_video':
        return redirect(url_for('webcam_video_capture'))
    else:
        return redirect(url_for('index'))

@app.route('/image_upload')
def image_upload_form():
    """Render the image upload form"""
    # Get unvisited sides
    unvisited_sides = [side for side in sides if not sides_status[side]['visited']]
    
    if not unvisited_sides:
        reset_system()
        unvisited_sides = sides
    
    return render_template('image_upload.html', unvisited_sides=unvisited_sides)

@app.route('/video_upload')
def video_upload_form():
    """Render the video upload form"""
    # Get unvisited sides
    unvisited_sides = [side for side in sides if not sides_status[side]['visited']]
    
    if not unvisited_sides:
        reset_system()
        unvisited_sides = sides
    
    return render_template('video_upload.html', unvisited_sides=unvisited_sides)

@app.route('/webcam_image')
def webcam_image_capture():
    """Render the webcam image capture page"""
    # Get unvisited sides
    unvisited_sides = [side for side in sides if not sides_status[side]['visited']]
    
    if not unvisited_sides:
        reset_system()
        unvisited_sides = sides
    
    return render_template('webcam_image.html', unvisited_sides=unvisited_sides)

@app.route('/webcam_video')
def webcam_video_capture():
    """Render the webcam video capture page"""
    # Get unvisited sides
    unvisited_sides = [side for side in sides if not sides_status[side]['visited']]
    
    if not unvisited_sides:
        reset_system()
        unvisited_sides = sides
    
    return render_template('webcam_video.html', unvisited_sides=unvisited_sides)

@app.route('/upload_images', methods=['POST'])
def upload_images():
    """Handle image uploads"""
    global processing_complete, available_time
    
    # Reset processing flag
    processing_complete = False
    
    # Get unvisited sides
    unvisited_sides = [side for side in sides if not sides_status[side]['visited']]
    
    if not unvisited_sides:
        reset_system()
        unvisited_sides = sides
    
    # Process each uploaded file
    for side in unvisited_sides:
        # Process incoming traffic
        incoming_key = f'incoming_image_{side}'
        
        if incoming_key in request.files:
            file = request.files[incoming_key]
            
            if file.filename != '' and allowed_image_file(file.filename):
                filename = secure_filename(f"{side}_incoming_{int(time.time())}.jpg")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Detect vehicles in the image
                incoming_count = detect_vehicles_in_image(filepath)
                sides_status[side]['incoming_vehicles'] = incoming_count
        
        # Process outgoing traffic
        outgoing_key = f'outgoing_image_{side}'
        
        if outgoing_key in request.files:
            file = request.files[outgoing_key]
            
            if file.filename != '' and allowed_image_file(file.filename):
                filename = secure_filename(f"{side}_outgoing_{int(time.time())}.jpg")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Detect vehicles in the image
                outgoing_count = detect_vehicles_in_image(filepath)
                sides_status[side]['outgoing_vehicles'] = outgoing_count
        
        # Calculate total vehicles for this side
        sides_status[side]['total_vehicles'] = (
            sides_status[side]['incoming_vehicles'] + sides_status[side]['outgoing_vehicles']
        )
    
    # After processing all sides, compute dynamic available time once
        available_time = compute_dynamic_available_time()
    print(f"DEBUG: computed available_time = {available_time} (total vehicles = {sum(sides_status[s]['total_vehicles'] for s in sides)})")

    # Calculate signal timings
    calculate_signal_time()
    
    return redirect(url_for('traffic_ui'))

@app.route('/upload_videos', methods=['POST'])
def upload_videos():
    """Handle video uploads"""
    global processing_complete, available_time
    
    # Reset processing flag
    processing_complete = False
    
    # Get unvisited sides
    unvisited_sides = [side for side in sides if not sides_status[side]['visited']]
    
    if not unvisited_sides:
        reset_system()
        unvisited_sides = sides
    
    # Process each uploaded file
    for side in unvisited_sides:
        # Process incoming traffic
        incoming_key = f'incoming_video_{side}'
        
        if incoming_key in request.files:
            file = request.files[incoming_key]
            
            if file.filename != '' and allowed_video_file(file.filename):
                filename = secure_filename(f"{side}_incoming_{int(time.time())}.mp4")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Detect vehicles in the video
                incoming_count = detect_vehicles_in_video(filepath)
                sides_status[side]['incoming_vehicles'] = incoming_count
        
        # Process outgoing traffic
        outgoing_key = f'outgoing_video_{side}'
        
        if outgoing_key in request.files:
            file = request.files[outgoing_key]
            
            if file.filename != '' and allowed_video_file(file.filename):
                filename = secure_filename(f"{side}_outgoing_{int(time.time())}.mp4")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Detect vehicles in the video
                outgoing_count = detect_vehicles_in_video(filepath)
                sides_status[side]['outgoing_vehicles'] = outgoing_count
        
        # Calculate total vehicles for this side
        sides_status[side]['total_vehicles'] = (
            sides_status[side]['incoming_vehicles'] + sides_status[side]['outgoing_vehicles']
        )
        # After processing all sides, compute dynamic available time once
        available_time = compute_dynamic_available_time()
    print(f"DEBUG: computed available_time = {available_time} (total vehicles = {sum(sides_status[s]['total_vehicles'] for s in sides)})")

    # Calculate signal timings
    calculate_signal_time()
    
    return redirect(url_for('traffic_ui'))

@app.route('/save_webcam_images', methods=['POST'])
def save_webcam_images():
    """Save webcam captured images and process them"""
    global processing_complete, available_time
    
    # Reset processing flag
    processing_complete = False
    
    data = request.get_json()
    
    # Get unvisited sides
    unvisited_sides = [side for side in sides if not sides_status[side]['visited']]
    
    if not unvisited_sides:
        reset_system()
        unvisited_sides = sides
    
    # Process each image data
    for side in unvisited_sides:
        # Process incoming traffic
        if f'incoming_{side}' in data:
            img_data = data[f'incoming_{side}'].split(',')[1]  # Remove data URL prefix
            img_bytes = np.frombuffer(base64.b64decode(img_data), np.uint8)
            img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
            
            filename = f"{side}_incoming_{int(time.time())}.jpg"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            cv2.imwrite(filepath, img)
            
            # Detect vehicles in the image
            incoming_count = detect_vehicles_in_image(filepath)
            sides_status[side]['incoming_vehicles'] = incoming_count
        
        # Process outgoing traffic
        if f'outgoing_{side}' in data:
            img_data = data[f'outgoing_{side}'].split(',')[1]  # Remove data URL prefix
            img_bytes = np.frombuffer(base64.b64decode(img_data), np.uint8)
            img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
            
            filename = f"{side}_outgoing_{int(time.time())}.jpg"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            cv2.imwrite(filepath, img)
            
            # Detect vehicles in the image
            outgoing_count = detect_vehicles_in_image(filepath)
            sides_status[side]['outgoing_vehicles'] = outgoing_count
        
        # Calculate total vehicles for this side
        sides_status[side]['total_vehicles'] = (
            sides_status[side]['incoming_vehicles'] + sides_status[side]['outgoing_vehicles']
        )
        available_time = compute_dynamic_available_time()
    print(f"DEBUG: computed available_time = {available_time} (total vehicles = {sum(sides_status[s]['total_vehicles'] for s in sides)})")
    # Calculate signal timings
    calculate_signal_time()
    
    return jsonify({'status': 'success', 'redirect': url_for('traffic_ui')})

@app.route('/save_webcam_videos', methods=['POST'])
def save_webcam_videos():
    """Save webcam recorded videos and process them"""
    global processing_complete, available_time
    
    # Reset processing flag
    processing_complete = False
    
    # Get unvisited sides
    unvisited_sides = [side for side in sides if not sides_status[side]['visited']]
    
    if not unvisited_sides:
        reset_system()
        unvisited_sides = sides
    
    # Process each uploaded file
    for side in unvisited_sides:
        # Process incoming traffic
        incoming_key = f'incoming_video_{side}'
        
        if incoming_key in request.files:
            file = request.files[incoming_key]
            
            if file.filename != '':
                filename = secure_filename(f"{side}_incoming_{int(time.time())}.webm")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Detect vehicles in the video
                incoming_count = detect_vehicles_in_video(filepath)
                sides_status[side]['incoming_vehicles'] = incoming_count
        
        # Process outgoing traffic
        outgoing_key = f'outgoing_video_{side}'
        
        if outgoing_key in request.files:
            file = request.files[outgoing_key]
            
            if file.filename != '':
                filename = secure_filename(f"{side}_outgoing_{int(time.time())}.webm")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Detect vehicles in the video
                outgoing_count = detect_vehicles_in_video(filepath)
                sides_status[side]['outgoing_vehicles'] = outgoing_count
        
        # Calculate total vehicles for this side
        sides_status[side]['total_vehicles'] = (
            sides_status[side]['incoming_vehicles'] + sides_status[side]['outgoing_vehicles']
        )
        available_time = compute_dynamic_available_time()
    print(f"DEBUG: computed available_time = {available_time} (total vehicles = {sum(sides_status[s]['total_vehicles'] for s in sides)})")
    # Calculate signal timings
    calculate_signal_time()
    
    return redirect(url_for('traffic_ui'))

@app.route('/traffic-ui')
def traffic_ui():
    """Render the traffic UI"""
    return render_template('traffic_ui.html')

@app.route('/get_signal_times')
def get_signal_times():
    """API endpoint to get current signal times"""
    # Get vehicle counts in same order as signals
    vehicle_counts = [sides_status[side]['total_vehicles'] for side in sides]
    incoming_counts = [sides_status[side]['incoming_vehicles'] for side in sides]
    outgoing_counts = [sides_status[side]['outgoing_vehicles'] for side in sides]
    
    response = {
        'signal_times': signal_times,
        'current_green': current_green,
        'vehicle_counts': vehicle_counts,
        'incoming_counts': incoming_counts,
        'outgoing_counts': outgoing_counts,
        'available_time': available_time,
        'processing_complete': processing_complete
    }
    
    return jsonify(response)

@app.route('/next_cycle', methods=['POST'])
def next_cycle():
    """API endpoint to proceed to next cycle"""
    global processing_complete
    processing_complete = False
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    import base64  # Import here to avoid circular import
    app.run(debug=True)
    