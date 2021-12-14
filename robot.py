class Robot:
    def preMount(self, puck_pos: int, pin_pos: int, samp_id: str, **kwargs):
        ...

    def mount(self, puck_pos: int, pin_pos: int, samp_id: str, **kwargs):
        ...

    def postMount(self, puck_pos: int, pin_pos: int, samp_id: str, **kwargs):
        ...

    def preUnmount(self, puck_pos: int, pin_pos: int, samp_id: str):
        ...

    def unmount(self, puck_pos: int, pin_pos: int, samp_id: str):
        ...