import os
import socket
import threading
import tkinter as tk
from tkinter import filedialog

# CONSTANTS
HOST = 'localhost'
PORT = 9999
CHUNK_SIZE = 1024*1024
DATA_FOLDER = 'Server_data'
socket_lock = threading.Lock() # Initialize the lock for thread-safe operations
    
# HANDLE CLIENT REQUESTS
def handle_client(conn,addr):
    print(f"Connected by {addr}")
    try:
        request_type, file_info = receive_request_type_and_file_info(conn)
        if not request_type or not file_info:
            raise ValueError("Invalid request type or file info")
        print(f"Request: {request_type}")
        print(f"File info: {file_info}")

        if request_type == 'upload':
            file_name, num_chunks = file_info.strip().split(':')
            num_chunks = int(num_chunks.strip())
            print(f"FileUploadname: {file_name}, num_chunks: {num_chunks}")
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
        
# UPLOAD
def handle_upload(conn, file_name,num_chunks):
    try:
        chunk_paths = [None] * num_chunks # Pre-allocate list for chunk paths
        
        # create and start the threads to receive chunk files
        threads = []
        for _ in range(num_chunks):
            thread = threading.Thread(target=receive_chunk, args=(conn, socket_lock, chunk_paths, file_name, num_chunks))
            threads.append(thread)
            thread.start()
            
        for thread in threads:
            thread.join()
            
        # Merge chunks if all were downloaded successfully
        if None not in chunk_paths:
            output_file = ensure_unique_filename(os.path.join(DATA_FOLDER, file_name))
            merge_chunks(chunk_paths, output_file)
            
            conn.sendall("OK".encode())
            print(f"File {file_name} uploaded successfully.")

    except Exception as e:
        print(f"Error handling upload: {e}")
        
def receive_chunk(conn, socket_lock, chunk_paths, file_name, num_chunks):
    try:
        with socket_lock:
            # Receive chunk info
            chunk_info = conn.recv(1024).decode().strip()
            chunk_index, chunk_size = map(int, chunk_info.split(':'))
            #  ACK for chunk info
            conn.sendall("OK".encode())
            
            # Receive chunk data
            chunk_data = b''
            while len(chunk_data) < chunk_size:
                chunk_data +=conn.recv(min(1024, chunk_size - len(chunk_data)))
                
            # Save the chunk data to a file
            chunk_path = os.path.join(DATA_FOLDER, f"{file_name}_chunk_{chunk_index}")
            with open(chunk_path, 'wb') as chunk_file:
                chunk_file.write(chunk_data)
            # ACK for a chunk
            conn.sendall("OK".encode())
            print(f"Received chunk_{chunk_index} size: {chunk_size} ({chunk_index + 1}/{num_chunks})")
            
            # Save chunk path
            chunk_paths[chunk_index] = chunk_path 
    except Exception as e:
        print(f"Error receiving chunk: {e}")
           
# DOWNLOAD
def handle_download(conn, file_name):
    try:
        # Get file path
        file_path = os.path.join(DATA_FOLDER, file_name)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_name} not found.")

        #  Split the file into chunks
        chunks = split_file(file_path, CHUNK_SIZE)
        num_chunks = len(chunks)
        conn.sendall(f"{num_chunks}".encode())  
        
        # Send chunks to the client
        threads = []
        for index, chunk_path in enumerate(chunks):
            thread = threading.Thread(target= send_chunk, args=(conn, index, chunk_path, num_chunks))
            threads.append(thread)
            thread.start()
            
        for thread in threads:
            thread.join()
        # ACK for send all chunks
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

def send_chunk(conn, chunk_index, chunk_path, num_chunks):
    try:
        with socket_lock:
            # Get chunk size
            chunk_size = os.path.getsize(chunk_path)
            conn.sendall(f"{chunk_index}:{chunk_size}\n".encode())
            # ACK for chunk size
            ack = conn.recv(10).decode().strip()
            if ack != 'OK':
                raise Exception("Failed to receive acknowledgment from client.")
            
            # Send chunk data
            with open(chunk_path, 'rb') as chunk_file:
                chunk_data = chunk_file.read()
                conn.sendall(chunk_data)
            # ACK for chunk data
            ack = conn.recv(10).decode().strip()
            if ack != 'OK':
                raise Exception("Failed to receive acknowledgment from client.")
            else:
                print(f"sent chunk_{chunk_index} size: {os.path.getsize(chunk_path)} ({chunk_index + 1}/{num_chunks})")
    except Exception as e:
        print(f"Error sending chunk {chunk_index}: {e}")
        
# HELPER FUNCTIONS
def receive_request_type_and_file_info(conn):
    # the request: {request_type}{file_name:num_chunks}
    data = conn.recv(1024).decode().strip()
    conn.sendall("OK".encode())
    
    if data.startswith('upload'):
        return 'upload', data[len('upload'):]
    elif data.startswith('download'):
        return 'download', data[len('download'):]

    else:
        return None, None
    
def ensure_unique_filename(file_path):
    base, ext = os.path.splitext(file_path)
    counter = 1
    unique_file_path = file_path
    
    while os.path.exists(unique_file_path):
        unique_file_path = f"{base}_{counter}{ext}"
        counter += 1
    
    return unique_file_path

def split_file(file_path, chunk_size):
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

def merge_chunks(chunks, output_file):
    with open(output_file, 'wb') as out_file:
        for chunk_file in chunks:
            with open(chunk_file, 'rb') as chunk:
                out_file.write(chunk.read())
            os.remove(chunk_file)

# START SERVER
def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        # Bind the socket to the host and port
        server_socket.bind((HOST,PORT))
        # Listen for incoming connections
        server_socket.listen()
        print(f"Server started on {HOST}:{PORT}")
        
        while True:
            # Accept a new connection
            conn, addr = server_socket.accept()
            print(f"Connected with client {addr[0]}:{addr[1]}")
            # Handle the client connection in a new thread
            client_thread = threading.Thread(target = handle_client, args = (conn,addr))
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
