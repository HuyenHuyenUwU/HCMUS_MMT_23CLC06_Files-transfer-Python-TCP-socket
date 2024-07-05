# # Logic của việc mà mình truyền file
# # Sender
# # Reciever
# # Upload: Data: client-> serever => client: gửi, server: nhận
# # Download: data đi từ server->client => client: nhận, server: gửi

# # Sender: 3 bước
# # 1. truy cập vào browser -> select folder
# # 2. SPLIT file thành N segment
# # 3. Tạo N thread tương ứng -> SEND 

# # Reciever: 3 bước
# # 1. Nhận N segments 
# # 2. MERGE các file đã nhận -> save vào 2 cái folder 
# # 3. (optional) xóa các file bị thừa

# #libraries
# import os
# import socket
# import tkinter #message box, tk, filedialog, simpledialog
# import threading

# #constant
# HOST = 'localhost' #127.0.0.1
# PORT = 9999
# CHUNK_SIZE = 1024 # 1kb
# UPLOAD_FOLDER = 'Client_data'

# #function
# select_file_to_upload() #Ngan

# # UPLOAD
# upload_file(file_path) # 1. split file thanh cac chunk nho -> chay mot vong for de gui tung chunk mot (nho kiem tra tat ca chunk da qua het chua)
# split_file(file_path, chunk_size) # tach file lon -> N files nho #Ngan
# # chunks[] -> code -> return chunks

# #DOWNLOAD
# recieve_file(filename, num_chunk)
# merge_chunks(chunks, outputfile) # tao mot file output moi -> chay mot vong for -> write tung chunk nho vao(nho kiem tra tat ca chunk da qua het chua)

# # main()
# # tao socket
# # tao connection -> signal connect with client nao
# # chen gui elements (button, thanh tien trinh, chu thich...)


# #main entry point

