from asyncio import Event


class ConcurrencyEvents:
    def __init__(self):
        self.should_accept_invite = Event()
        self.has_accepted_invite = Event()
