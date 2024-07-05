# Logic của việc mà mình truyền file
# Sender
# Reciever
# Upload: Data: client-> serever => client: gửi, server: nhận
# Download: data đi từ server->client => client: nhận, server: gửi

# Sender: 3 bước
# 1. truy cập vào browser -> select folder
# 2. SPLIT file thành N segment
# 3. Tạo N thread tương ứng -> SEND 

# Reciever: 3 bước
# 1. Nhận N segments 
# 2. MERGE các file đã nhận -> save vào 2 cái folder 
# 3. (optional) xóa các file bị thừa
#libraries
import os
import socket
import tkinter #message box, tk, filedialog, simpledialog
import threading

#constant
HOST = 'localhost' #127.0.0.1
PORT = 9999
CHUNK_SIZE = 1024 # 1kb
UPLOAD_FILE  = 'Server_data'

#function
handle_client(conn, addr) # xu li yeu cau tu client
# try:
# request type: command tu client
# == 'upload' -> handle_upload
# == 'download' -> handle download
# except: invalid request (error)
# finally: conn.close()

handle_upload()
# 1. Nhận N segments 
# 2. MERGE các file đã nhận -> save vào 2 cái folder 
merge_chunks(chunks, outputfile)
# 3. (optional) xóa các file bị thừa

handle_download()
# Sender: 3 bước
# 1. truy cập vào browser -> select folder
# 2. SPLIT file thành N segment
split_file(file_path, chunk_size) 
select_file_to_download()

# 3. Tạo N thread tương ứng -> SEND 

start_server()
# tao socket
# tao connection -> signal connect with client nao
# chen gui elements (button, thanh tien trinh, chu thich...)
# hoac print nhung cai tin hieu cmd
#ex:
# connecting to client 1...
# recieve filename form client1...





