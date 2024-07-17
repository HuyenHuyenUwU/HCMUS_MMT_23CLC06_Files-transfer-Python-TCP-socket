import os
import socket
import threading
#import tkinter as tk
from tkinter import *
from tkinter import filedialog, simpledialog, ttk

# CONSTANTS
HOST = 'localhost'
PORT = 9999
CHUNK_SIZE = 1024
DOWNLOAD_FOLDER = 'Client_data'
socket_lock = threading.Lock()

# UPLOAD
def upload_chunk(chunk_index, chunk_path, client_socket, socket_lock):
    try:
        with socket_lock:
            client_socket.sendall(f"{chunk_index}:{os.path.getsize(chunk_path)}\n".encode())
            print(f"{chunk_index}:{os.path.getsize(chunk_path)}".encode())
            ack = client_socket.recv(1024).decode().strip()
            if ack != "OK":
                raise Exception("Failed to receive acknowledgment from server.")

            with open(chunk_path, 'rb') as chunk_file:
                chunk_data = chunk_file.read()
                client_socket.sendall(chunk_data)

            ack = client_socket.recv(1024).decode().strip()
            if ack != "OK":
                raise Exception("Failed to receive acknowledgment from server.")
    except Exception as e:
        print(f"Error sending chunk {chunk_path}: {e}")

def upload_file(file_path):
    try:
        chunks = split_file(file_path, CHUNK_SIZE)
        num_chunks = len(chunks)
        print(f"Num of chunks: {num_chunks}")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((HOST, PORT))
            client_socket.sendall("upload".encode())
            file_info = f"{os.path.basename(file_path)}:{num_chunks}"
            client_socket.sendall(file_info.encode())
            ack = client_socket.recv(1024).decode().strip()
            if ack != "OK":
                raise Exception("Failed to receive acknowledgment from server.")
            print(file_info.encode())

            threads = []
            for index, chunk_path in enumerate(chunks):
                thread = threading.Thread(target=upload_chunk, args=(index, chunk_path, client_socket, socket_lock))
                threads.append(thread)
                thread.start()
            for thread in threads:
                thread.join()

    except Exception as e:
        print(f"Error uploading file {file_path}: {e}")
    finally:
        for chunk in chunks:
            os.remove(chunk)

        
# DOWNLOAD
def download_file(file_name, client_socket, chunk_paths):
    try:
        with socket_lock:
            chunk_info = client_socket.recv(1024).decode().strip()
            print(f"chunk_info: {chunk_info}\n")
            chunk_index, chunk_size = map(int, chunk_info.split(':'))
            print(f"chunk_index: {chunk_index}\n")
            print(f"chunk_size: {chunk_size}\n")
            client_socket.send('OK'.encode())

            chunk_data = b''
            while len(chunk_data) < chunk_size:
                chunk_data += client_socket.recv(min(1024, chunk_size - len(chunk_data)))

            chunk_path = os.path.join(DOWNLOAD_FOLDER, f"{file_name}_chunk_{chunk_index}")
            with open(chunk_path, 'wb') as chunk_file:
                chunk_file.write(chunk_data)

            client_socket.send('OK'.encode())
            chunk_paths.append(chunk_path)

    except Exception as e:
        print(f"Error downloading file {file_name}: {e}")

def download_files(file_name):
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
            client_socket.sendall(file_name.encode())
            print(f"Send filename to server: {file_name.encode()}")
            ack = client_socket.recv(1024).decode().strip()
            if ack != "OK":
                raise Exception("Failed to receive acknowledgment from server.")
            # Receive the number of chunks
            num_chunks = int(client_socket.recv(1024).decode())
            print(f"Num of chunks: {num_chunks}")
            
            # Send acknowledgment
            chunk_paths = []

            threads = []
            for _ in range(num_chunks):
                thread = threading.Thread(target=download_file, args=(file_name, client_socket, chunk_paths))
                threads.append(thread)
                thread.start()
            for thread in threads:
                thread.join()
            
            if None not in chunk_paths:
                output_file = os.path.join(DOWNLOAD_FOLDER, file_name)
                merge_chunks(chunk_paths, output_file)
                print(f"File {file_name} downloaded successfully.")


    except socket.error as E:
        print(f"Socket error: {E}")
    except Exception as E:
        print(f"Error: {E}")
    
# ACCESS TO BROWSER
def select_file_to_upload():
    '''
    window=Toplevel(root)
    window.title("Upload")
    window.geometry("300x250+300+300")
    window.configure(bg="linen")
    window.resizable(False,False)
    '''
    
    file_path = filedialog.askopenfilename(initialdir=os.getcwd(),
                                            title='Select Image File',
                                            filetype=(('file_type','*.txt'),('all files','*.*')))
    if file_path:
        upload_file(file_path)
        print(f"File selected: {file_path}")
    else:
        print("No file selected to upload.")
        
def select_file_to_download():
    '''
    main=Toplevel(root)
    main.title("Download")
    main.configure("300x250+300+300")
    main.resizable(False,False)
    '''
    
    file_name = simpledialog.askstring("Download", "Enter the filename to download:")
    if file_name:
        download_files(file_name)
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
    root = Tk()
    root.title("File Transfer Application")
    root.geometry("300x250+300+300")
    root.configure(bg="linen")
    root.resizable(False,False)

    #App icon 
    image_icon = PhotoImage(file="Image/icon1.png")
    root.iconphoto(False,image_icon)


    upload_image = PhotoImage(file="Image/upload.png")
    upload = Button(root,image=upload_image,bg="linen", bd=0,command=select_file_to_upload)
    upload.place(x=50,y=50)
    Label(root,text="Upload",font=('arial', 16, 'bold'),bg='linen').place(x=45,y=125)

    download_image = PhotoImage(file="Image/download.png")
    download = Button(root,image=download_image,bg="linen",bd=0,command=select_file_to_download)
    download.place(x=185,y=50)
    Label(root,text="Download",font=('arial', 16, 'bold'),bg='linen').place(x=165,y=125)
    
    root.mainloop()
    
if __name__ == "__main__":
    main()
