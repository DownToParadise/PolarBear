import queue
from collections import Counter

class YoloQueue:
    def __init__(self, max_size=30) -> None:
        self.q = queue.Queue(maxsize=max_size)
        self.preds = {}
        self.max_size = max_size

    # 设置FIFO规则
    def enqueue(self, item):
        if self.q.qsize() >= self.max_size:
            self.q.get()
        label, acc = item
        self.preds[label] = acc
        self.q.put(item)

    # 获取所有元素
    def get_all_items(self):
        items = []
        for item in self.q.queue:
            items.append(item[0])
        return items

    def find_most_frequent(self):
        items = self.get_all_items()
        if items:
            counter = Counter(items)
            most_common_item = counter.most_common(1)[0][0]
            return most_common_item, self.preds[most_common_item]
        else:
            return None
        
    def if_full_queue(self):
        if self.q.qsize < self.max_size:
            return False
        else:
            return True
        
    # 加入标签优先级
        
# cq = YoloQueue()

# 测试
# # 添加超过30个元素的情况测试
# for i in range(35):
#     cq.enqueue(f"item_{i % 5}")  # 模拟重复添加元素

# # 找到出现最多的成员
# most_frequent = cq.find_most_frequent()
# print(f"Most frequent item: {most_frequent}")

# # 打印队列中的元素
# print(f"Current queue: {cq.get_all_items()}")