import os
import socket
import threading
import tkinter as tk
from tkinter import filedialog, simpledialog, ttk

# CONSTANTS
HOST = 'localhost'
PORT = 9999
CHUNK_SIZE = 1024
UPLOAD_FOLDER = 'Server_data'

# HANDLE REQUEST TYPE AND FILE INFO
def receive_request_type_and_file_info(conn):
    data = conn.recv(100).decode().strip()
    
    if data.startswith('upload'):
        return 'upload', data[len('upload'):]
    elif data.startswith('download'):
        return 'download', data[len('download'):]
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
        
def handle_upload(conn, file_name, num_chunks):
    try:
        chunks = []
        # Receive chunks from client
        for i in range(num_chunks):
            # Receive chunk size
            chunk_size = int(conn.recv(1024).decode().strip())
            conn.sendall(b"OK")
            
            # Receive chunk data
            chunk = b''
            while len(chunk) < chunk_size:
                received_data = conn.recv(chunk_size - len(chunk))
                if not received_data:
                    raise ConnectionResetError("Connection closed before receiving the entire chunk.")
                chunk += received_data
            
            if len(chunk) != chunk_size:
                raise ValueError(f"Chunk {i+1} received with incorrect size: {len(chunk)} bytes")
                
            # Create a unique path for each chunk file
            chunk_path = f"chunk_{i+1}.bin" # binary files
            chunk_path = os.path.join(UPLOAD_FOLDER, chunk_path)
            print(f"Chunk path of chunk_{i+1}.bin: {chunk_path}")
            
            with open(chunk_path, 'wb') as chunk_file:
                chunk_file.write(chunk)
            chunks.append(chunk_path)
            print(f"Received chunk {i+1}/{num_chunks}")
        
        # Merge chunks into output file
        output_file_path = os.path.join(UPLOAD_FOLDER, file_name)
        merge_chunks(chunks, output_file_path)
        print(f"Merge file success. New file path is: {output_file_path}")
                
        print(f"File {file_name} received and merged successfully")
        conn.sendall(b"OK")
        
    except socket.error as E:
        print(f"Socket error: {E}")
    except OSError as E:
        print(f"Error writing to file: {E}")
    except Exception as E:
        print(f"Error: {E}")

def handle_download(conn, file_name):
    try:
        file_path = os.path.join(UPLOAD_FOLDER, file_name)
        if os.path.exists(file_path):
            print(f"Filename: {file_name}")
            file_size = os.path.getsize(file_path)
            num_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
            print(f"Num of chunks: {num_chunks}")
            conn.sendall(f"{num_chunks}\n".encode())
            print(f"send: {num_chunks}")
            
            # Wait for acknowledgment
            ack = conn.recv(1024).decode().strip()
            if ack != "OK":
                raise Exception("Failed to receive acknowledgment from client.")
            
            with open(file_path, 'rb') as f:
                for i in range(num_chunks):
                    chunk = f.read(CHUNK_SIZE)
                    chunk_size = len(chunk)
                    
                    # Send chunk size
                    conn.sendall(f"{chunk_size}\n".encode())
                    
                    # Wait for acknowledgment
                    ack = conn.recv(1024).decode().strip()
                    if ack != "OK":
                        raise Exception("Failed to receive acknowledgment from client.")
                    
                    # Send chunk data
                    conn.sendall(chunk)
                    print(f"Send chunk {i+1}/{num_chunks}")
                    
            print(f"File {file_name} sent to client.")
        else:
            conn.sendall(b"ERROR: File not found")
            print(f"Error: File {file_name} not found.")
    except FileNotFoundError:
        conn.sendall(b"ERROR: File not found")
        print(f"Error: File {file_name} not found.")
    except OSError as e:
        conn.sendall(b"ERROR: Server encountered an issue reading the file")
        print(f"OS error: {e}")
    except Exception as e:
        conn.sendall(b"ERROR: An unexpected error occurred")
        print(f"Unexpected error: {e}")
        
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