from asyncio import Semaphore


class SyncTaskSems:
    def __init__(self):
        self.num_export_process_sem = Semaphore(0)
