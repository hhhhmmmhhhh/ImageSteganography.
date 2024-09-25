from PIL import Image
from itertools import permutations
import io
import socket
import random
#解码
#从二进制字符串转为utf-8字符串
def binaryToString(binary):
    index=0
    string=[]
    rec=lambda x,i:x[2:8]+(rec(x[8:],i-1) if i>1 else '') if x else ''
    fun = lambda x,i:x[i+1:8]+rec(x[8:], i-1)
    while index+1<len(binary):
        chartype=binary[index:].index('0') #存放字符所占字节数，一个字节的字符会存为0
        length=chartype*8 if chartype else 8
        string.append(chr(int(fun(binary[index:index+length],chartype),2)))
        index+=length
    return ''.join(string)

#乱序
def shuffle_based_on_n(s, n):
    random.seed(n)
    s_list = list(s)
    indices = list(range(len(s_list)))
    random.shuffle(indices)
    encoded = ''.join(s_list[i] for i in indices)
    return indices
#反乱序
def decode(encoded, indices):
    decoded_list = [None] * len(indices)
    for i, idx in enumerate(indices):
        decoded_list[idx] = encoded[i]

    return ''.join(decoded_list)

#获取长度
def decode_length(image):
    if image.size[0] < 32 or image.mode != 'RGBA':
        raise Exception("Image must be at least 32 pixels wide and in RGBA mode.")
    # 读取前32个像素的g通道
    pixels = list(image.getdata())[:32]
    binary_length = ''
    for pixel in pixels:
        r, g, b, a = pixel
        # 提取绿色通道的最低位
        binary_length += str(int(g >> 1 << 1 != g))
    #将二进制字符串转换回整数
    data_length = int(binary_length, 2)
    return data_length

#散列
def hash_indices(image_size, data_length):
    total_pixels = image_size[0] * image_size[1]  # 图片总像素数
    bits_per_pixel = 4  # RGBA每个像素4个位（每个通道1位）
    max_bits = total_pixels * bits_per_pixel
    # 确保可以存储所有数据
    if data_length > max_bits:
        raise ValueError("图片无法存储这么多数据")
        # 计算每个数据位之间的平均间隔
    avg_interval = max(1, max_bits//(data_length))
    # 生成索引列表
    indices = [i * avg_interval for i in range(data_length)]
    # 确保索引不会超出图片像素范围
    indices = [idx % max_bits for idx in indices]
    # 转换为像素索引（考虑每个像素有4个位）
    pixel_indices = [idx // bits_per_pixel for idx in indices]
    # 转换为二维索引（x, y）
    width, height = image_size
    x_indices = [idx % width for idx in pixel_indices]
    y_indices = [idx // width for idx in pixel_indices]
    return list(zip(y_indices, x_indices))

#解码数据
def decodeImage(image):
    indices=hash_indices(image.size, decode_length(image))
    '''
    with open('indices.txt', 'r') as f:
        data = f.read()
        indices = [tuple(map(int, item.strip('()').split(','))) for item in data.split('),(')]
        #print(indices)
        
    with open('encoded.txt', 'r') as f:
        lines = f.readlines()
        encoded = lines[0].strip()
        indices_ = list(map(int, lines[0].strip().split(',')))
    '''

    pixels=list(image.getdata()) #获得编码后的像素列表
    binary = ""

    for index,(y,x) in enumerate(indices):
        if 0 <= x < image.width and 0 <= y < image.height:
            pixel=image.getpixel((x,y))
            if len(pixel) == 4:
                r, g, b, t = pixel
                # 检查r的最低位
                r_binary = str(int(r >> 1 << 1 != r))
                #str(int(t >> 1 << 1 != t))
            binary += r_binary
    #找到数据截至处的标志，返回索引
    locationDoubleNull = binary.find('0000000000000000')
    if locationDoubleNull == -1:
        locationDoubleNull = len(binary)
    binary = binary[:locationDoubleNull]
    indices_ = shuffle_based_on_n(binary, n=123456789)
    binary_ = decode(binary, indices_)
    # 不足位补0
    endIndex = locationDoubleNull + (
                    8 - (locationDoubleNull % 8)) if locationDoubleNull % 8 != 0 else locationDoubleNull
    data=binaryToString(binary_[0:endIndex])
    return data

#通信
def decode_image_from_socket(host, port):
    # 创建socket并绑定地址
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, port))
        sock.listen(5)

        # 接受连接
        print("正在等待一个连接...")
        conn, addr = sock.accept()
        print(f"接受一个客户端连接{addr}")

        # 接收图片数据的大小
        data_size = int.from_bytes(conn.recv(4), 'big')

        # 接收图片数据
        encoded_image_data = b''
        while len(encoded_image_data)<data_size:
            encoded_image_data += conn.recv(4096)

        #将接收到的数据转换为图片并解码
        encoded_image = Image.open(io.BytesIO(encoded_image_data))
        decoded_data = decodeImage(encoded_image)

        print("解码得到的隐藏信息是:", decoded_data)

if __name__ == '__main__':
    #img_src = input('请输入需要解码的图片路径：')
    #print(decodeImage(Image.open('Image.png')))
    decode_image_from_socket('localhost',9006)

    #data_length = decode_length(Image.open('image.png'))
    #print(data_length)