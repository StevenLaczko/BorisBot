from queue import PriorityQueue


class PriorityQueuePeek(PriorityQueue):
    def peek(self):
        temp = self.get()
        self.put(temp)
        return temp
