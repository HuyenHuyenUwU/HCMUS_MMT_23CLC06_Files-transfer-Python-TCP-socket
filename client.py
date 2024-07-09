import os
import socket
import threading
import tkinter as tk
from tkinter import filedialog, simpledialog, ttk

# constants
HOST = 'localhost'
PORT = 9999
CHUNK_SIZE = 1024
UPLOAD_FOLDER = 'Client_data'
DOWNLOAD_FOLDER = 'Client_data'

# UPLOAD
def upload_file(file_path):
    try:
        # split file into chunks (chunks[] contain file_path)
        chunks = split_file(file_path, CHUNK_SIZE)
        num_chunks = len(chunks)
        
        # create socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.settimeout(10)  # Set a timeout to prevent hanging connections
            
            # connect to server
            client_socket.connect((HOST,PORT))
            
            # send request type
            client_socket.sendall(b"upload")
            
            # send file info: {file_path}:{num_chunks}
            file_info = f"{os.path.basename(file_path)}:{num_chunks}"
            client_socket.sendall(file_info.encode())
            
            # send each chunk
            for chunk_path in chunks:
                try:
                    with open(chunk_path, 'rb') as chunk_file:
                        # send each byte in chunk
                        while True:
                            chunk_data = chunk_file.read(CHUNK_SIZE)
                            if not chunk_data:
                                break
                            client_socket.sendall(chunk_data)
                except OSError as E:
                    print(f"Error reading chunk file: {E}")
                    continue
                
            print(f"File {file_path} uploaded successfully.")
    except socket.error as E:
        print(f"Socket error: {E}")
    except Exception as E:
        print(f"Error: {E}")
        
    finally:
        # close the connection
        if client_socket:
            client_socket.close()
        
# DOWNLOAD

# access to browser
def select_file_to_upload():
    file_path = filedialog.askopenfilename()
    if file_path:
        upload_file(file_path)
        print(f"File selected: {file_path}")
    else:
        print("No file selected to upload.")
        
def select_file_to_download():
    file_name = simpledialog.askstring("Download", "Enter the filename to download:")
    if file_name:
        #download_file(file_path)
        print(f"File selected: {file_name}")
    else:
        print("No file selected to download.") 
        

# helper functions
def split_file(file_path, chunk_size):
    # intialize a list to stores chunks
    chunks = []
    # open the file in read-binary mode
    with open(file_path, 'rb') as file:
        # read the file chunks-by-chunks
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                chunk_filename = f"{file_path}_part_{len(chunks)}"
                # open file in write-binary mode and write each chunks to new file
                with open(chunk_filename, 'wb') as chunk_file:
                    chunk_file.write(chunk)
                chunks.append(chunk_filename)
    # return list of chunk_path
    return chunks

def merge_chunks(chunks, output_file):
    with open(output_file, 'wb') as out_file:
        for chunk_file in chunks:
            with open(chunk_file, 'rb') as chunk:
                out_file.write(chunk.read())
            os.remove(chunk_file)

def main():
    global root
    root = tk.Tk() # main window
    root.title("File transfer Application")
    
    upload_button = tk.Button(root, text = "Upload file", command = select_file_to_upload)
    upload_button.pack()
    
    # download_button = tk.Button(root, text = "Download file", command = select_file_to_download()).pack
    # download_button.pack()
    
    root.mainloop()
    
if __name__ == "__main__":
    main()