import subprocess


class AlbulaInterface:
    _instance = None  # For a singleton
    _init_args = None
    _process = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AlbulaInterface, cls).__new__(cls)
            cls._init_args = (args, kwargs)
        return cls._instance

    def __init__(self, *args, **kwargs):
        if self._init_args is None:
            self._init_args = (args, kwargs)
            self.open(args, kwargs)

    def _call(self, code):
        response = ""
        if self._process:
            print(code, file=self._process.stdin, flush=True)

            if self._process.stdout:
                response = self._process.stdout.readline()
        return response

    def open_file(self, filename):
        if isinstance(filename, str):
            index = None
        else:
            # For rasters filename is passed in as a tuple of filename and image index
            filename = filename[0]
            index = filename[1]
        result = self._call(f'albulaController.albulaDispFile("{filename}", {index})')
        print(result)

    def close(self):
        if self._process is None:
            return
        if self._process.stdin:
            self._process.stdin.close()
        self._process.terminate()

    def open(self, args, kwargs):
        if self._process is not None:
            return
        self._process = subprocess.Popen(
            [
                kwargs["python_path"],
                "-u",
                "-i",
                "./gui/albula/controller.py",
            ],  # -u for unbuffered I/O, -i to keep stdin open
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        if "ip" in kwargs and "gov_message_pv_name" in kwargs:
            self._call(
                f'albulaController.setup_monitor({kwargs["ip"]}, {kwargs["gov_message_pv_name"]})'
            )
