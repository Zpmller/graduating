import cv2
import numpy as np

class ImageEnhancer:
    def __init__(self, method='clahe', clip_limit=2.0, tile_grid_size=(8, 8)):
        """
        Initialize the Image Enhancer.
        
        Args:
            method (str): 'clahe' (Contrast Limited Adaptive Histogram Equalization) or 'he' (Global Histogram Equalization).
            clip_limit (float): Threshold for contrast limiting (for CLAHE).
            tile_grid_size (tuple): Size of grid for histogram equalization (for CLAHE).
        """
        self.method = method.lower()
        self.clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)

    def enhance(self, frame):
        """
        Apply enhancement to the input frame.
        
        Args:
            frame (numpy.ndarray): Input BGR image.
            
        Returns:
            numpy.ndarray: Enhanced BGR image.
        """
        if frame is None:
            return None

        # Convert to LAB color space
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Apply enhancement to the L-channel
        if self.method == 'clahe':
            l_enhanced = self.clahe.apply(l)
        elif self.method == 'he':
            l_enhanced = cv2.equalizeHist(l)
        else:
            return frame # No enhancement

        # Merge channels and convert back to BGR
        lab_enhanced = cv2.merge((l_enhanced, a, b))
        frame_enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

        return frame_enhanced
