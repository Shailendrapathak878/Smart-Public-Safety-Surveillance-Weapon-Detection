import cv2
import numpy as np
from typing import Generator, Tuple, Optional, Union

class StreamManager:
    """
    Unified stream abstraction for Webcam, IP Camera, RTSP, Video File, and Static Image.
    Yields (frame, source_name).
    """
    def __init__(self, source: Union[int, str, bytes], source_type: str):
        self.source = source
        self.source_type = source_type
        self.cap = None

    def _init_capture(self) -> bool:
        if self.source_type in ["webcam", "ip_camera", "rtsp", "video"]:
            # source is an int (e.g., 0) or string (e.g., URL or path)
            try:
                if self.source_type == "webcam" or (isinstance(self.source, str) and self.source.isdigit()):
                    self.cap = cv2.VideoCapture(int(self.source))
                else:
                    # Setting timeout or using default OpenCV
                    self.cap = cv2.VideoCapture(self.source)
                return self.cap.isOpened()
            except Exception as e:
                print(f"Error initializing capture for {self.source}: {e}")
                return False
        return True

    def get_frames(self) -> Generator[Tuple[Optional[np.ndarray], str], None, None]:
        """
        Yields frames from the configured source.
        """
        if self.source_type == "image":
            # source is expected to be bytes of the image
            if isinstance(self.source, bytes):
                nparr = np.frombuffer(self.source, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                yield frame, "Static Image"
            else:
                yield None, "Static Image Error"
            return

        if not self._init_capture():
            yield None, f"Failed to open {self.source_type}"
            return

        source_name = f"Stream ({self.source})" if isinstance(self.source, str) else f"Webcam {self.source}"
        
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                # Convert BGR to RGB for Streamlit/YOLO consistency
                # Wait, YOLO handles BGR natively usually, but Streamlit expects RGB.
                # We will yield BGR here, and let UI convert for display, YOLO expects BGR from cv2.
                yield frame, source_name
        finally:
            self.release()

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
