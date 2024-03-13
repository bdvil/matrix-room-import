from asyncio import Semaphore


class SyncTaskSems:
    def __init__(self, initial_processes: int = 0):
        self.num_export_process_sem = Semaphore(initial_processes)
