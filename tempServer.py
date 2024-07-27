import os
import socket
import threading
import tkinter as tk
from tkinter import *
from tkinter import filedialog, ttk

# CONSTANTS
HOST = 'localhost'
PORT = 9999
CHUNK_SIZE = 1024*1024
UPLOAD_FOLDER = 'Client_data'
socket_lock = threading.Lock() # Initialize the lock for thread-safe operations
    
# HANDLE CLIENT REQUESTS

class FileServer:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((HOST, PORT))
        self.server_socket.listen()
        self.files_info = []
        self.window = None
        self.tree = None

    def start(self):
        print(f"Server started on {HOST}:{PORT}")
        while True:
            conn, addr = self.server_socket.accept()
            print(f"Connected with client {addr[0]}:{addr[1]}")
            client_handler = ClientHandler(conn, addr, self)
            client_thread = threading.Thread(target = client_handler.handle_client)
            client_thread.start()


    def display_files_info(self):
        # Create a new Tkinter window to display the file info
        self.window = tk.Tk()
        self.window.title("Uploaded Files")
        self.window.geometry("500x600")

        self.tree = ttk.Treeview(self.window, columns=("ID", "File Name"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("File Name", text="File Name")
        self.tree.pack(fill="both", expand=True)

        self.update_file_list()
        self.window.mainloop()

    def update_file_list(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        for index, file_info in enumerate(self.files_info):
            self.tree.insert("", tk.END, values=(index + 1, file_info["Name"]))

        self.window.after(1000, self.update_file_list)

class ClientHandler:
    def __init__(self, conn, addr, server):
        self.conn = conn
        self.addr = addr
        self.server = server

    def handle_client(self):
        try:
            request_type, file_info = self.receive_request_type_and_file_info()
            if not request_type or not file_info:
                raise ValueError("Invalid request type or file info")
            print(f"Request: {request_type}")
            print(f"File info: {file_info}")

            if request_type == 'upload':
                file_name, num_chunks = file_info.strip().split(':')
                num_chunks = int(num_chunks.strip())
                print(f"FileUpload name: {file_name}, num_chunks: {num_chunks}")
                self.handle_upload(file_name, num_chunks)

            elif request_type == 'download':
                file_name = file_info.strip()
                print(f"FileDownload name: {file_name}")
                self.handle_download(file_name)

            else:
                print(f"Unknow request type: {request_type}")

        except socket.error as E:
            print(f"Socket error: {E}")
        except OSError as E:
            print(f"Error writing to file: {E}")
        except ValueError as E:
            print(f"Error parsing file info: {E}")
        except Exception as E:
            print(f"Error: {E}")
        finally:
            self.conn.close()

    # HELPER FUNCTIONS
    def receive_request_type_and_file_info(self):
        # the request: {request_type}{file_name:num_chunks}
        data = self.conn.recv(1024).decode().strip()
        self.conn.sendall("OK".encode())
        
        if data.startswith('upload'):
            return 'upload', data[len('upload'):]
        elif data.startswith('download'):
            return 'download', data[len('download'):]

        else:
            return None, None            
         
    # UPLOAD
    def handle_upload(self, file_name,num_chunks):
        try:
            chunk_paths = [None] * num_chunks # Pre-allocate list for chunk paths
            
            # create and start the threads to receive chunk files
            threads = []
            for _ in range(num_chunks):
                thread = threading.Thread(target=self.receive_chunk, args=(chunk_paths, file_name, num_chunks))
                threads.append(thread)
                thread.start()
                
            for thread in threads:
                thread.join()
                
            # Merge chunks if all were downloaded successfully
            if None not in chunk_paths:
                output_file = self.ensure_unique_filename(os.path.join(UPLOAD_FOLDER, file_name))
                self.merge_chunks(chunk_paths, output_file)
                
                self.conn.sendall("OK".encode())
                print(f"File {file_name} uploaded successfully.")
                self.server.files_info.append({"Name": file_name})

        except Exception as e:
            print(f"Error handling upload: {e}")
        
    def receive_chunk(self, chunk_paths, file_name, num_chunks):
        try:
            with socket_lock:
                # Receive chunk info
                chunk_info = self.conn.recv(1024).decode().strip()
                chunk_index, chunk_size = map(int, chunk_info.split(':'))
                #  ACK for chunk info
                self.conn.sendall("OK".encode())
                
                # Receive chunk data
                chunk_data = b''
                while len(chunk_data) < chunk_size:
                    chunk_data +=self.conn.recv(min(1024, chunk_size - len(chunk_data)))
                    
                # Save the chunk data to a file
                chunk_path = os.path.join(UPLOAD_FOLDER, f"{file_name}_chunk_{chunk_index}")
                with open(chunk_path, 'wb') as chunk_file:
                    chunk_file.write(chunk_data)
                # ACK for a chunk
                self.conn.sendall("OK".encode())
                print(f"Received chunk_{chunk_index} size: {chunk_size} ({chunk_index + 1}/{num_chunks})")
                
                # Save chunk path
                chunk_paths[chunk_index] = chunk_path 
        except Exception as e:
            print(f"Error receiving chunk: {e}")

    # DOWNLOAD
    def handle_download(self, file_name):
        try:
            # Get file path
            file_path = os.path.join(UPLOAD_FOLDER, file_name)
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File {file_name} not found.")

            #  Split the file into chunks
            chunks = self.split_file(file_path, CHUNK_SIZE)
            num_chunks = len(chunks)
            self.conn.sendall(f"{num_chunks}".encode())  
            
            # Send chunks to the client
            threads = []
            for index, chunk_path in enumerate(chunks):
                thread = threading.Thread(target=self.send_chunk, args=(index, chunk_path, num_chunks))
                threads.append(thread)
                thread.start()
                
            for thread in threads:
                thread.join()
            # ACK for send all chunks
            ack = self.conn.recv(10).decode().strip()
            if ack != 'OK':
                raise Exception("Failed to receive acknowledgment from client.")
            else:
                print(f"File {file_name} downloaded successfully.")
        except Exception as e:
            print(f"Error handling download: {e}")
        finally:
            for chunk in chunks:
                os.remove(chunk)

    def send_chunk(self, chunk_index, chunk_path, num_chunks):
        try:
            with socket_lock:
                # Get chunk size
                chunk_size = os.path.getsize(chunk_path)
                self.conn.sendall(f"{chunk_index}:{chunk_size}\n".encode())
                # ACK for chunk size
                ack = self.conn.recv(10).decode().strip()
                if ack != 'OK':
                    raise Exception("Failed to receive acknowledgment from client.")
                
                # Send chunk data
                with open(chunk_path, 'rb') as chunk_file:
                    chunk_data = chunk_file.read()
                    self.conn.sendall(chunk_data)
                # ACK for chunk data
                ack = self.conn.recv(10).decode().strip()
                if ack != 'OK':
                    raise Exception("Failed to receive acknowledgment from client.")
                else:
                    print(f"sent chunk_{chunk_index} size: {os.path.getsize(chunk_path)} ({chunk_index + 1}/{num_chunks})")
        except Exception as e:
            print(f"Error sending chunk {chunk_index}: {e}")
        
    def ensure_unique_filename(self, file_path):
        base, ext = os.path.splitext(file_path)
        counter = 1
        unique_file_path = file_path
        
        while os.path.exists(unique_file_path):
            unique_file_path = f"{base}_{counter}{ext}"
            counter += 1
        
        return unique_file_path

    def split_file(self, file_path, chunk_size):
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

    def merge_chunks(self, chunks, output_file):
        with open(output_file, 'wb') as out_file:
            for chunk_file in chunks:
                with open(chunk_file, 'rb') as chunk:
                    out_file.write(chunk.read())
                os.remove(chunk_file)


def main():
    server = FileServer()
    try:
        threading.Thread(target=server.start, daemon=True).start()
        server.display_files_info()
    
    except KeyboardInterrupt:
        print("Server stopped.")
    except Exception as E:
        print(f"Error: {E}")

if __name__ == "__main__":
    main()

