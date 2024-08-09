import os
import socket
import threading
import tkinter as tk
import pandas as pd
from tkinter import *
from tkinter import filedialog, simpledialog, ttk

# CONSTANTS
HOST = 'localhost'
PORT = 9999
CHUNK_SIZE = 1024*1024
UPLOAD_FOLDER = 'Server_data'
socket_lock = threading.Lock() # Lock for synchronizing socket access

# UPLOAD
def upload_file(file_path):
    try:
        # Split the file into chunks
        chunks = split_file(file_path, CHUNK_SIZE)
        num_chunks = len(chunks)
        print(f"Num of chunks: {num_chunks}")
        
        # Create a socket for the client
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            # Connect to the server
            client_socket.connect((HOST,PORT))
            # Send the request type
            client_socket.sendall('upload'.encode())
            
            # Send the file info
            file_info = f"{os.path.basename(file_path)}:{num_chunks}"
            client_socket.sendall(file_info.encode())
            # ACK for receving file info
            ack = client_socket.recv(1024).decode().strip()
            if ack != 'OK':
                raise Exception("Failed to receive acknowledgment from server.")
            
            # Create threads to upload each chunk
            threads = []
            # Start threads
            for index, chunk_path in enumerate(chunks):
                thread = threading.Thread(target = upload_chunk, args = (index, chunk_path,client_socket, socket_lock, num_chunks))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads finish
            for thread in threads:
                thread.join()
                
            # Final ACK
            ack = client_socket.recv(1024).decode().strip()
            if ack != 'OK':
                raise Exception("Failed to receive acknowledgment from server.")
            else:
                print(f"File {file_path} uploaded successfully.")
    except Exception as e:
        print(f"Error uploading file {file_path}: {e}")
    finally:
        # Clean up chunk file
        for chunk in chunks:
            if(os.path.exists(chunk)):
                os.remove(chunk)
            
def upload_chunk(chunk_index, chunk_path, client_socket, socket_lock, num_chunks):
    try:
        # Synchronize access to the socket
        with socket_lock:
            #Send chunk index and size
            client_socket.sendall(f"{chunk_index}:{os.path.getsize(chunk_path)}\n".encode())
            # ACK for chunk index and size
            ack = client_socket.recv(1024).decode().strip()
            if ack != "OK":
                raise Exception("Failed to receive acknowledgment from server.")
            
            # Open and send the chunk data to the server
            with open(chunk_path, 'rb') as chunk_file:
                chunk_data = chunk_file.read()
                client_socket.sendall(chunk_data)
                
            # ACK for finishing a chunk file
            ack = client_socket.recv(1024).decode().strip()
            if ack != "OK":
                raise Exception("Failed to receive acknowledgment from server.")
            else:
                print(f"sent chunk_{chunk_index} size: {os.path.getsize(chunk_path)} ({chunk_index + 1}/{num_chunks})")
    except Exception as e:
        print(f"Error sending chunk {chunk_path}: {e}")
        
# DOWNLOAD
def download_file(file_path):
    try:
        # create socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            # connect to server
            client_socket.connect((HOST, PORT))
            print(f"Host: {HOST}, Port: {PORT}")
            
            # Send the request type
            client_socket.sendall("download".encode())
            print(f"Send request to server: {"download".encode()}")
            
            # Send the file name
            client_socket.sendall(file_path.encode())
            print(f"Send filename to server: {file_path.encode()}")
            # ACK for receving file name
            ack = client_socket.recv(1024).decode().strip()
            if ack != "OK":
                raise Exception("Failed to receive acknowledgment from server.")
            
            # Receive the number of chunks
            num_chunks = int(client_socket.recv(1024).decode())
            print(f"Num of chunks: {num_chunks}")
            
            # Open dialog to choose destination of download folder 
            download_folder_path = filedialog.askdirectory()
            if not download_folder_path:
                print("No download folder selected.")
                return
            
            # Init list to store chunk paths and threads
            chunk_paths = []
            threads = []
            for _ in range(num_chunks):
                thread = threading.Thread(target = download_chunk, args = (file_path, client_socket, chunk_paths, num_chunks, download_folder_path, socket_lock))
                threads.append(thread)
                thread.start()
                
            for thread in threads:
                thread.join()
                
            # Merge chunks if all were downloaded successfully
            if None not in chunk_paths:
                output_file = os.path.join(download_folder_path, os.path.basename(ensure_unique_filename(file_path, download_folder_path))) # ensure the file names are unique
                merge_chunks(chunk_paths, output_file)
                
                client_socket.send('OK'.encode())
                print(f"File {file_path} downloaded successfully.")
    except socket.error as E:
        print(f"Socket error: {E}")
    except Exception as E:
        print(f"Error: {E}")

def download_chunk(file_path, client_socket, chunk_paths, num_chunks, download_folder_path,socket_lock):
    try:
        with socket_lock:
            # Receive chunk info
            chunk_info = client_socket.recv(1024).decode().strip()
            chunk_index, chunk_size = map(int, chunk_info.split(':'))
            # ACK for chunk info
            client_socket.send('OK'.encode()) 
            
            # Receive chunk data
            chunk_data = b''
            while len(chunk_data) < chunk_size:
                chunk_data += client_socket.recv(min(1024, chunk_size - len(chunk_data)))
                
            #  Save the chunk data to a file
            chunk_path = os.path.join(download_folder_path, f"{file_path}_chunk_{chunk_index}")
            with open(chunk_path, 'wb') as chunk_file:
                chunk_file.write(chunk_data)
                
            # ACK for chunk data
            client_socket.send('OK'.encode())
            print(f"Received chunk_{chunk_index} size: {chunk_size} ({chunk_index + 1}/{num_chunks})")
            chunk_paths.append(chunk_path)
    except Exception as e:
        print(f"Error downloading file {file_path}: {e}")

# ACCESS TO BROWSER
def select_file_to_upload():
    # Open file dialog to select a file for upload
    file_paths = filedialog.askopenfilenames(initialdir = os.getcwd(), title = 'Select File to Upload', filetypes = (('all files', '*.*'),))
    for file_path in file_paths:
        if file_path:
            upload_file(file_path)
            print(f"File selected: {file_path}")
        else:
            print("No file selected to upload.")
    
def select_file_to_download():
    # Open file dialog to select a filefrom 'Server_data' folder
    file_paths = filedialog.askopenfilenames(initialdir = UPLOAD_FOLDER, title = 'Select File to Download', filetypes = (('all files', '*.*'),))
    
    for file_path in file_paths:
        if file_path:
            download_file(file_path)
            print(f"File selected: {file_path}")
        else:
            print("No file selected to download.")

# HELPER FUNCTIONS
def ensure_unique_filename(file_path, download_folder_path): # Ensure the filename is unique by appending a number if the file already exists
    base, ext = os.path.splitext(file_path)
    counter = 1
    file_name = os.path.basename(file_path)
    unique_file_path = os.path.join(os.path.basename(download_folder_path),file_name)
    
    while os.path.exists(unique_file_path):
        unique_file_path = f"{base}_{counter}{ext}"
        counter += 1
    
    return unique_file_path

def split_file(file_path, chunk_size): # Split the file into chunks of specified size
    chunks = []
    with open(file_path, 'rb') as file:
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            chunk_filename = f"{file_path}_part_{len(chunks)}"
            with open(chunk_filename, 'wb') as chunk_file:
                chunk_file.write(chunk)
            chunks.append(chunk_filename)
    return chunks

def merge_chunks(chunks, output_file): # Merge the chunks into a single output file
    with open(output_file, 'wb') as out_file:
        for chunk_file in chunks:
            with open(chunk_file, 'rb') as chunk:
                out_file.write(chunk.read())
            os.remove(chunk_file)
            

def main():
    # Initialize the Tkinter root window
    global root
    
    root = Tk()
    root.title("File Transfer Application")
    root.geometry("300x250+300+300")
    root.configure(bg="linen")
    root.resizable(False,False)

    # App Icon
    image_icon = PhotoImage(file="Image/icon1.png")
    root.iconphoto(False,image_icon)

    # Upload button
    upload_image = PhotoImage(file="Image/upload.png")
    upload = Button(root,image=upload_image,bg="linen", bd=0,command=select_file_to_upload)
    upload.place(x=50,y=50)
    Label(root,text="Upload",font=('arial', 16, 'bold'),bg='linen').place(x=45,y=125)
    
    # Download button
    download_image = PhotoImage(file="Image/download.png")
    download = Button(root,image=download_image,bg="linen",bd=0,command=select_file_to_download)
    download.place(x=185,y=50)
    Label(root,text="Download",font=('arial', 16, 'bold'),bg='linen').place(x=165,y=125)
    
    root.mainloop()
    
if __name__ == "__main__":
    main()