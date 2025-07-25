import cv2, threading

class Camera:
    def __init__(self, device=0, width=1920, height=1080):
        self.cap = cv2.VideoCapture(device, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(device)
        if not self.cap.isOpened():
            raise RuntimeError("Cannot open camera")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        self._lock     = threading.Lock()
        self._ret, self._frame = self.cap.read()          
        self._running  = False
        self._thread   = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._update, daemon=True)
        self._thread.start()

    def read(self):
        with self._lock:
            return self._ret, self._frame.copy()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()
        self.cap.release()

    def _update(self):
        while self._running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            with self._lock:
                self._ret, self._frame = ret, frame
