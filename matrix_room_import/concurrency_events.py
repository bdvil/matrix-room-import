from asyncio import Semaphore


class ConcurrencyEvents:
    def __init__(self):
        self.num_export_process_sem = Semaphore(0)
