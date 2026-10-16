import pytest
import cv2
import numpy as np
from streams.stream_manager import StreamManager

def test_static_image_stream():
    # Create a dummy image
    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
    _, buffer = cv2.imencode('.jpg', dummy_img)
    img_bytes = buffer.tobytes()

    manager = StreamManager(source=img_bytes, source_type="image")
    generator = manager.get_frames()
    
    frame, source_name = next(generator)
    
    assert frame is not None
    assert frame.shape == (100, 100, 3)
    assert source_name == "Static Image"

    # Next iteration should raise StopIteration
    with pytest.raises(StopIteration):
        next(generator)
