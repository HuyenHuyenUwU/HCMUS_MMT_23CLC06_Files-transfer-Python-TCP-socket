import os
import socket
import threading
import tkinter as tk
from tkinter import filedialog, simpledialog, ttk

# constants
HOST = 'localhost'
PORT = 9999
CHUNK_SIZE = 1024
UPLOAD_FOLDER = 'Server_data'

# handle client
def handle_client(conn, addr):
    print(f"Connected by {addr}")
    try:
        request_type = conn.recv(1024).decode()
    
        if request_type == 'upload':
            file_info = conn.recv(1024).decode()
            file_name, num_chunks = file_info.split(':')
            num_chunks = int(num_chunks)
            handle_upload(conn, file_name, num_chunks)
            
        elif request_type == 'download':
            file_name = conn.recv(1024).decode()
            handle_download(conn, file_name)
    
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
            chunk = b''
            while len(chunk) < CHUNK_SIZE:
                received_data = conn.recv(CHUNK_SIZE - len(chunk))
                if not received_data:
                    raise ConnectionResetError("Connection closed before receiving the entire chunk.")
                chunk += received_data
                
            # Create a unique path for each chunk file
            chunk_path = f"chunk_{i+1}.bin" # binary files
            chunk_path = os.path.join(UPLOAD_FOLDER, chunk_path)
            with open(chunk_path, 'wb') as chunk_file:
                chunk_file.write(chunk)
            chunks.append(chunk_path)
            print(f"Received chunk {i+1}/{num_chunks}")
        
        # Merge chunks into output file
        output_file_path = os.path.join(UPLOAD_FOLDER, file_name)
        merge_chunks(chunks, output_file_path)
        
        # delete remain files in chunks[]
        for chunk_path in chunks:
            try:
                os.remove(chunk_path)
            except OSError as E:
                print(f"Error deleting chunk file {chunk_file}: {E}.")
                
        print(f"File {file_name} received and merged successfully")
        
    except socket.error as E:
        print(f"Socket error: {E}")
    except OSError as E:
        print(f"Error writing to file: {E}")
    except Exception as E:
        print(f"Error: {E}")
    except socket.error as E:
        print(f"Socket error: {E}")
    except OSError as E:
        print(f"Error writing to file: {E}")
    except Exception as E:
        print(f"Error: {E}") 

def handle_download(conn, file_name):
    try:
        if os.path.exists(file_name):
            # Send the file size and number of chunks
            file_size = os.path.getsize(file_name)
            num_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
            conn.sendall(f"{num_chunks}".encode())

            # Send the file in chunks
            with open(file_name, 'rb') as f:
                for _ in range(num_chunks):
                    chunk = f.read(CHUNK_SIZE)
                    conn.sendall(chunk)
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
        chunk_num = 0
        # read the file chunks-by-chunks
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            chunk_path = f"{file_path}_part_{len(chunks)}"
            # open file in write-binary mode and write each chunks to new file
            with open(chunk_path, 'wb') as chunk_file:
                chunk_file.write(chunk)
                chunks.append(chunk_path)
                chunk_num += 1
    # return list of chunk_path
    return chunks

def merge_chunks(chunks, output_file):
    with open(output_file, 'wb') as out_file:
        for chunk_file in chunks:
            with open(chunk_file, 'rb') as chunk:
                out_file.write(chunk.read())
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





