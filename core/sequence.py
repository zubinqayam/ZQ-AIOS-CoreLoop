class SequenceGenerator:
    def __init__(self):
        self._seq = 0

    def next(self):
        self._seq += 1
        return self._seq

SEQ_GEN = SequenceGenerator()
