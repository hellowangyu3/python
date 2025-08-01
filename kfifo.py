from log import log_wp


class KFifoAps:
    """环形队列实现，对应C语言中的kfifo_aps"""

    # 环形缓冲大小，对应C中的FIFO_QUEUE_LEN
    FIFO_QUEUE_LEN = 32 * 256 * 2

    def __init__(self, buffer_size=None):
        """初始化环形队列"""
        # 如果未指定大小，使用默认队列长度
        self.size = buffer_size if buffer_size else self.FIFO_QUEUE_LEN
        self.buffer = [0] * self.size
        self.in_pos = 0  # 写入位置，对应C中的in
        self.out_pos = 0  # 读取位置，对应C中的out
        self.length = 0  # 当前数据长度

    def get_remaining_length(self):
        """获取fifo剩余空间大小，对应get_kfifo_aps_len"""
        return self.size - self.length

    def put(self, data):
        """
        向kfifo中添加数据，对应kfifo_aps_put
        data: 要添加的字节数据（bytes或整数列表，元素0-255）
        返回实际添加的数据长度
        """
        # 修复1：检查数据类型（仅允许bytes或整数列表）
        if not isinstance(data, (bytes, list)):
            log_wp(f"put错误：不支持的数据类型 {type(data)}，仅允许bytes或整数列表")
            return 0

        # 修复2：若为bytes类型，转换为整数列表（与缓冲区存储格式统一）
        if isinstance(data, bytes):
            data = list(data)  # bytes → [0x01, 0x02, ...]（整数列表）

        # 修复3：检查列表元素是否为有效字节值（0-255的整数）
        if isinstance(data, list):
            for i, byte in enumerate(data):
                if not isinstance(byte, int) or byte < 0 or byte > 255:
                    print(f"put错误：列表元素 {i} 不是有效字节值（{byte}）")
                    return 0

        if not data:
            return 0

        # 原有逻辑：计算可添加长度（保持不变）
        if self.length > self.FIFO_QUEUE_LEN:
            self.length = self.FIFO_QUEUE_LEN
            return 0

        data_len = len(data)
        if (self.length + data_len) > self.FIFO_QUEUE_LEN:
            add_len = self.FIFO_QUEUE_LEN - self.length
        else:
            add_len = data_len

        if add_len <= 0:
            return 0

        # 复制数据到缓冲区（此时data已确保为整数列表，可安全赋值）
        start = self.length
        self.buffer[start:start + add_len] = data[:add_len]
        self.length += add_len

        return add_len

    def get(self, length):
        """
        从kfifo中取数据，对应kfifo_aps_get
        length: 要读取的数据长度
        返回读取到的数据（字节列表）
        """
        if length <= 0 or self.length == 0:
            return []

        # 计算实际可读取的长度
        read_len = min(length, self.length)
        if read_len <= 0:
            return []

        # 读取数据
        data = self.buffer[:read_len]

        # 移动剩余数据
        for i in range(self.length - read_len):
            self.buffer[i] = self.buffer[i + read_len]

        self.length -= read_len
        return data

    def free(self, length):
        """释放指定长度的kfifo空间，对应kfifo_aps_free"""
        if length <= 0:
            return

        if length >= self.FIFO_QUEUE_LEN or length >= self.length:
            self.length = 0
        else:
            # 移动数据
            for i in range(self.length - length):
                self.buffer[i] = self.buffer[i + length]
            self.length -= length

    def get_data_length(self):
        """获取kfifo当前数据长度，对应kfifo_aps_datalen_get"""
        return self.length

    def read(self, length):
        """读取kfifo中的数据，不清空fifo，对应kfifo_read"""
        if length <= 0 or self.length == 0:
            return []

        read_len = min(length, self.length)
        return self.buffer[:read_len].copy()

    def read_index(self, index, length):
        """
        从指定索引读取数据，对应kfifo_aps_read_index
        index: 起始索引
        length: 要读取的长度
        返回读取到的数据
        """
        if self.length > self.FIFO_QUEUE_LEN:
            self.length = self.FIFO_QUEUE_LEN

        # 检查索引是否有效
        if index < 0 or (index + length) > self.length:
            return []

        return self.buffer[index:index + length].copy()

    def __str__(self):
        """打印队列信息"""
        return f"KFifoAps(size={self.size}, length={self.length}, data={self.buffer[:self.length]})"


# 使用示例
if __name__ == "__main__":
    # 创建队列实例
    fifo = KFifoAps()

    # 添加数据
    data = [0x01, 0x12, 0x03, 0x14, 0x05]
    added = fifo.put(data)
    print(f"添加了 {added} 字节数据")
    print(f"当前队列长度: {fifo.get_data_length()}")

    # # 读取数据（不删除）
    # read_data = fifo.read(3)
    # print(f"读取到的数据: {[hex(x) for x in read_data]}")
    # print(f"读取后队列长度: {fifo.get_data_length()}")

    # 获取数据（删除）
    get_data = fifo.get(3)
    print(f"获取到的数据: {[hex(x) for x in get_data]}")
    print(f"获取后队列长度: {fifo.get_data_length()}")

    # 再添加一些数据
    data2 = "whudwhduw"
    fifo.put(data2)
    print(f"添加后队列长度: {fifo.get_data_length()}")
    print(f"队列内容: {fifo}")

    # 释放空间
    fifo.free(2)
    print(f"释放后队列长度: {fifo.get_data_length()}")
    print(f"释放后队列内容: {fifo}")
