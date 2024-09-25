import itertools
import random
from PIL import Image
import io
import socket
'''
#取一个PIL图像并更改所有值为偶数(使最低有效位为0)
def makeImageEven(image):
    pixels=list(image.getdata()) #得到一个这样的列表：[(r,g,b,A),(r,g,b,A)]
    evenPixels=[(r>>1<<1,g>>1<<1,b>>1<<1,t>>1<<1) for [r,g,b,t] in pixels] #列表推导式，更改所有值为偶数
    evenImage=Image.new(image.mode,image.size) #创建一个相同大小的图片副本
    evenImage.putdata(evenPixels)
    return evenImage
'''
#内置函数bin()的替代，返回固定长度的二进制字符串
def constLenBin(int):
    #去掉bin()返回的二进制字符串的0b
    binary="0"*(8-(len(bin(int))-2))+bin(int).replace('0b','')
    return binary

#字符串乱序
def shuffle_based_on_n(s, n):
    random.seed(n)
    s_list = list(s)
    indices = list(range(len(s_list)))
    random.shuffle(indices)
    encoded = ''.join(s_list[i] for i in indices)
    return encoded, indices


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



#隐藏长度
def hide_length(image, data):
    #转换数据长度为二进制字符串，并补全到32位
    data_length = len(data)
    binary_length = format(data_length, '032b')
    print(binary_length)
    #确保图像至少有32个像素
    if image.size[0] < 32 or image.mode != 'RGBA':
        raise Exception("Image must be at least 32 pixels wide and in RGBA mode.")

    pixels = list(image.getdata())
    # 隐藏长度信息到前32个像素的g通道中
    for i, pixel in enumerate(pixels[:32]):
        r, g, b, a = pixel
        # 只修改绿色通道的最低位
        g_new = (g & ~1) | int(binary_length[i])
        pixels[i] = (r, g_new, b, a)
    #创建一个新的图像来保存修改后的像素数据
    encoded_image = Image.new(image.mode, image.size)
    encoded_image.putdata(pixels)
    return encoded_image


#将字符串编码到图片里
#@image：载体图片
#@data:隐藏字符串
def encodeDataInImage(image,data):
    #evenImage=makeImageEven(image) #获得最低有效位为0的图片副本
    binary=''.join(map(constLenBin,bytearray(data,encoding='utf-8'))) #将需要被隐藏的字符串转换成二进制字符串
    print(len(binary))

    encoded_image=hide_length(image,binary)
    #encoded_image.save('encoded_image.png')

    #evenImage = makeImageEven(encoded_image)  # 获得最低有效位为0的图片副本
    #乱序
    binary_, indices = shuffle_based_on_n(binary, n=123456789)
    '''
    with open('encoded.txt', 'w') as f:
        f.write(','.join(map(str, indices)))
        '''

    if len(binary_)>len(encoded_image.getdata())*4: #如果不可能编码全部数据，抛出异常，*4是因为每个像素rgba有四个分量，即四个最低有效位
        raise Exception(f'Error: Can not encode more than {len(encoded_image.getdata()) * 4} bits in this image.')
    #encodedPixels=[(r+int(binary_[index*4+0]),g+int(binary_[index*4+1]),b+int(binary_[index*4+2]),t+int(binary_[index*4+3]))
                  # if index*4<len(binary_) else(r,g,b,t) for index,(r,g,b,t) in enumerate(list(evenImage.getdata()))] #把需要隐藏的信息都编码到像素的最低位中
    # 创建一个空列表来存储编码后的像素值
    encodedPixels = []
    width,height=encoded_image.size

    indices_=hash_indices(encoded_image.size,len(binary))
    '''
    with open('indices.txt', 'w') as f:
        f.write(','.join(map(str, indices_)))
        '''
    print(len(indices_))
    pixels = list(encoded_image.getdata())
    # 遍历每个像素及其索引
    index=-1
    for y in range(height):
        for x in range(width):
            if (y,x) in indices_:
                index+=1
                pixel=encoded_image.getpixel((x,y))
                r,g,b,t=pixel
                if index < len(binary_):
                # 将像素的RGBA值与二进制字符串中的相应位相加
                  r=(r & ~1) | int(binary_[index])
                encodedPixels.append((r,g,b,t))
            else:
                encodedPixels.append(encoded_image.getpixel((x,y)))

    encodeImage=Image.new(encoded_image.mode,encoded_image.size) #创建新图片以存放编码后的像素
    encodeImage.putdata(encodedPixels) #添加编码后的数据
    return encodeImage
#通信
def send_encoded_image(image_path, data, host, port):
    # 加载并编码图片
    image = Image.open(image_path).convert("RGBA")
    encoded_image = encodeDataInImage(image, data)

    # 将编码后的图片转换为字节流
    encoded_image_bytes = io.BytesIO()
    encoded_image.save(encoded_image_bytes, format='PNG')
    encoded_image_data = encoded_image_bytes.getvalue()

    # 创建socket连接
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        # 发送图片数据的大小（帮助接收方知道要接收多少数据）
        sock.sendall(len(encoded_image_data).to_bytes(4, 'big'))
        # 发送编码后的图片数据
        sock.sendall(encoded_image_data)
    encoded_image.save('image.png', format='PNG')


if __name__ == '__main__':
    '''
    img_src = input('请输入图片路径：')
    data= input('请输入要加密的信息：')
    '''
    #encodeDataInImage(Image.open('test.jpg').convert("RGBA"), 'yincangdexinxi').save('Image.png')
    send_encoded_image('test.jpg', 'yincangdexinxi', host='localhost', port=9006)