import os
import socket
import threading
import tkinter as tk
from tkinter import filedialog, simpledialog, ttk
from datetime import datetime

# CONSTANTS
UPLOAD_FOLDER = 'Server_data'
HOST = 'localhost'
PORT = 9999
CHUNK_SIZE = 1024*1024
UPLOAD_FOLDER = 'Server_data'
socket_lock = threading.Lock()

os.makedirs(UPLOAD_FOLDER, exist_ok = True)

# HANDLE REQUEST TYPE AND FILE INFO
def receive_request_type_and_file_info(conn):
    data = conn.recv(1024).decode().strip()
    conn.sendall("OK".encode())
    if data.startswith('upload:'):
        return 'upload', data[len('upload:'):]
    elif data.startswith('download:'):
        return 'download', data[len('download:'):]
    else:
        return None, None
    
# HANDLE CLIENT REQUESTS
def handle_client(conn, addr):
    print(f"Connected by {addr}")
    try:
        request_type, file_info = receive_request_type_and_file_info(conn)
        if not request_type or not file_info:
            raise ValueError("Invalid request type or file info")
        print(f"Request: {request_type}")
        print(f"File info: {file_info}")

        if request_type == 'check':
            check_file_existence(conn, file_info.strip())
        elif request_type == 'upload':  
            file_name, num_chunks = file_info.strip().split(':')
            num_chunks = int(num_chunks.strip())
            print(f"FileUploadname: {file_name}, num_chunks: {num_chunks}")

            # Check for existing file and handle naming conflict
            file_name = handle_file_name_conflict(file_name)

            handle_upload(conn, file_name, num_chunks)
            
        elif request_type == 'download':
            file_name = file_info.strip()
            print(f"FileDownloadname: {file_name}")
            handle_download(conn, file_name)
            
        else:
            print(f"Unknown request type: {request_type}")
    
    except socket.error as E:
        print(f"Socket error: {E}")
    except OSError as E:
        print(f"Error writing to file: {E}")
    except ValueError as E:
        print(f"Error parsing file info: {E}")
    except Exception as E:
        print(f"Error: {E}")
    finally:
        conn.close()

# HANDLE FILE EXISTENCE CHECKS
def check_file_existence(conn, file_name):
    file_path = os.path.join(UPLOAD_FOLDER, file_name)
    if os.path.exists(file_path):
        conn.sendall("EXISTS".encode())
    else:
        conn.sendall("NOT_EXISTS".encode())

# HANDLE FILE NAME CONFLICT
def handle_file_name_conflict(file_name):
    # Check if the file already exists in the upload folder
    file_path = os.path.join(UPLOAD_FOLDER, file_name)
    if os.path.exists(file_path):
        # Append a timestamp to the file name to make it unique
        base, ext = os.path.splitext(file_name)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        new_file_name = f"{base}_{timestamp}{ext}"
        print(f"File {file_name} exists. Remaining to {new_file_name}.")
        return new_file_name
    return file_name

#UPLOAD
def receive_chunk(conn, socket_lock, chunk_paths, file_name, num_chunks):
    try:
        with socket_lock:
            chunk_info = conn.recv(1024).decode().strip()
            chunk_index, chunk_size = map(int, chunk_info.split(':'))
            conn.sendall("OK".encode())
            chunk_data = b''
            while len(chunk_data) < chunk_size:
                chunk_data += conn.recv(min(1024, chunk_size - len(chunk_data)))

            chunk_path = os.path.join(UPLOAD_FOLDER, f"{file_name}_chunk_{chunk_index}")
            with open(chunk_path, 'wb') as chunk_file:
                chunk_file.write(chunk_data)

            conn.sendall("OK".encode())
            print(f"Received chunk_{chunk_index} size: {chunk_size} ({chunk_index + 1}/{num_chunks})")
            chunk_paths[chunk_index] = chunk_path  # Store chunk path at correct index
    except Exception as e:
        print(f"Error receiving chunk: {e}")

def handle_upload(conn, file_name, num_chunks):
    try:
        chunk_paths = [None] * num_chunks  # Pre-allocate list for chunk paths
        # Create a thread to receive each chunk
        threads = []
        for _ in range(num_chunks):
            thread = threading.Thread(target=receive_chunk, args=(conn, socket_lock, chunk_paths, file_name, num_chunks))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        
        if None not in chunk_paths:
            output_file = os.path.join(UPLOAD_FOLDER, file_name)
            merge_chunks(chunk_paths, output_file)
            conn.sendall("OK".encode())
            print(f"File {file_name} uploaded successfully.")

    except Exception as e:
        print(f"Error handling upload: {e}")

#DOWNLOAD
def send_chunk(conn, chunk_index, chunk_path, num_chunks):
            try:
                with socket_lock:
                    chunk_size = os.path.getsize(chunk_path)
                    conn.sendall(f"{chunk_index}:{chunk_size}\n".encode())
                    ack = conn.recv(10).decode().strip()
                    if ack != 'OK':
                        raise Exception("Failed to receive acknowledgment from client.")

                    with open(chunk_path, 'rb') as chunk_file:
                        chunk_data = chunk_file.read()
                        conn.sendall(chunk_data)

                    ack = conn.recv(10).decode().strip()
                    if ack != 'OK':
                        raise Exception("Failed to receive acknowledgment from client.")
                    else:
                        print(f"sent chunk_{chunk_index} size: {os.path.getsize(chunk_path)} ({chunk_index + 1}/{num_chunks})")
            except Exception as e:
                print(f"Error sending chunk {chunk_index}: {e}")


def handle_download(conn, file_name):
    try:
        file_path = os.path.join(UPLOAD_FOLDER, file_name)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_name} not found.")

        chunks = split_file(file_path, CHUNK_SIZE)
        num_chunks = len(chunks)
        conn.sendall(f"{num_chunks}".encode())        
        threads = []
        for index, chunk_path in enumerate(chunks):
            thread = threading.Thread(target=send_chunk, args=(conn, index, chunk_path, num_chunks))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        ack = conn.recv(10).decode().strip()
        if ack != 'OK':
            raise Exception("Failed to receive acknowledgment from client.")
        else:
            print(f"File {file_name} downloaded successfully.")
    except Exception as e:
        print(f"Error handling download: {e}")
    finally:
        for chunk in chunks:
            os.remove(chunk)
        
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

# start server
def start_server():
    # create socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        # connect to clients
        server_socket.bind((HOST,PORT))
        # listen for clients's requests
        server_socket.listen()
        print(f"Server started on {HOST}:{PORT}")
        
        while True:
            # lay connection va address
            conn, addr = server_socket.accept()
            print(f"Connected with client {addr[0]}:{addr[1]}")
            # chia thread ket noi voi tung client
            client_thread = threading.Thread(target = handle_client, args = (conn, addr))
            client_thread.start()

def main():
    try:
        start_server()
    except KeyboardInterrupt:
        print(f"Server stopped.")
    except Exception as E:
        print(f"Error: {E}")
    
if __name__ == "__main__":
    main()
