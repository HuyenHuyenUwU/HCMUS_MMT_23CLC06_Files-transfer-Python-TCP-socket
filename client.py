import os
import socket
import threading
import tkinter as tk
from tkinter import filedialog, simpledialog, ttk

# CONSTANTS
HOST = 'localhost'
PORT = 9999
CHUNK_SIZE = 1024
DOWNLOAD_FOLDER = 'Client_data'

# UPLOAD
def upload_file(file_path):
    try:
        # split file into chunks (chunks[] contain file_path)
        chunks = split_file(file_path, CHUNK_SIZE)
        num_chunks = len(chunks)
        print(f"Num of chunks: {num_chunks}")
        
        # create socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            # connect to server
            client_socket.connect((HOST,PORT))
            print(f"Host: {HOST}, Port: {PORT}")
            
            # send request type
            client_socket.sendall("upload\n".encode())
            print(f"Send request to server: {"upload".encode()}")
            
            # send file info: {file_path}:{num_chunks}
            file_info = f"{os.path.basename(file_path)}:{num_chunks}\n"
            client_socket.sendall(file_info.encode())
            print(f"Send file info to server: {file_info.encode()}")
            
            # send each chunk
            for chunk_path in chunks:
                try:
                    with open(chunk_path, 'rb') as chunk_file:
                        chunk_data = chunk_file.read()
                        chunk_size = len(chunk_data)
                        
                        # send chunk size
                        client_socket.sendall(f"{chunk_size}\n".encode())
                        
                        # wait for acknowledgment from server
                        ack = client_socket.recv(1024).decode().strip()
                        if ack != "OK":
                            raise Exception("Failed to receive acknowledgment from server.")
                        
                        # send chunk data
                        client_socket.sendall(chunk_data)
                        
                        print(f"Send chunk file: {chunk_path}")
                            
                except OSError as E:
                    print(f"Error reading chunk file: {E}")
                    continue
                
            print(f"File {file_path} uploaded successfully.")
    except socket.error as E:
        print(f"Socket error: {E}")
    except Exception as E:
        print(f"Error: {E}")
        
    finally:
        for chunk in chunks:
            os.remove(chunk)
        
# DOWNLOAD
def download_file(filename):
    try:
        #create socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            # connect to server
            client_socket.connect((HOST, PORT))
            print(f"Host: {HOST}, Port: {PORT}")
            
            # Send the request type
            client_socket.sendall("download".encode())
            print(f"Send request to server: {"download".encode()}")
            
            # Send the file name
            client_socket.sendall(filename.encode())
            print(f"Send filename to server: {filename.encode()}")
            
            # Receive the number of chunks
            num_chunks = int(client_socket.recv(1024).decode())
            print(f"Num of chunks: {num_chunks}")
            
            # Send acknowledgment
            client_socket.sendall(b"OK")
                
            chunks = []
            for i in range(num_chunks):
                # Receive chunk size
                chunk_size = int(client_socket.recv(1024).decode().strip())
                client_socket.sendall(b"OK")
                    
                # Receive chunk data
                chunk = b''
                while len(chunk) < chunk_size:
                    received_data = client_socket.recv(chunk_size - len(chunk))
                    if not received_data:
                        raise ConnectionResetError("Connection closed before receiving the entire chunk.")
                    chunk += received_data
                    
                if len(chunk) != chunk_size:
                    raise ValueError(f"Chunk {i+1} received with incorrect size: {len(chunk)} bytes")
                    
                chunk_filename = f"{filename}_part_{i}"
                with open(chunk_filename, 'wb') as chunk_file:
                    chunk_file.write(chunk)
                chunks.append(chunk_filename)
                print(f"Received chunk {i+1}/{num_chunks}")
                
            # Merge chunks into the final file
            output_file = os.path.join(DOWNLOAD_FOLDER, filename)
            merge_chunks(chunks, output_file)
            print(f"File {filename} downloaded successfully")
    
    except socket.error as E:
        print(f"Socket error: {E}")
    except Exception as E:
        print(f"Error: {E}")
    
# ACCESS TO BROWSER
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
        download_file(file_name)
        print(f"File selected: {file_name}")
    else:
        print("No file selected to download.") 
        

# HELPER FUNCTIONS
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
    # Open the output file in write-binary mode ('wb')
    with open(output_file, 'wb') as out_file:
        # Iterate over the list of chunk files
        for chunk_file in chunks:
            # Open the current chunk file in read-binary mode ('rb')
            with open(chunk_file, 'rb') as chunk:
                # Read the contents of the chunk file and write it to the output file
                out_file.write(chunk.read())
            # Remove the chunk file after it has been written to the output file
            os.remove(chunk_file)

def main():
    global root
    root = tk.Tk() # main window
    root.title("File transfer Application")
    
    # upload button
    upload_button = tk.Button(root, text = "Upload file", command = select_file_to_upload)
    upload_button.pack()
    
    # download button
    download_button = tk.Button(root, text = "Download file", command = select_file_to_download)
    download_button.pack() 
    
    root.mainloop()
    
if __name__ == "__main__":
    main()
