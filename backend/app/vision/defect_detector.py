import cv2
import numpy as np

class DefectDetector:
    @staticmethod
    def check_deformity(contour):
        """ 
        Simple deformity check based on contour fullness within bounding box.
        Returns: True if deformed, False if normal.
        """
        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            return True 
            
        area = cv2.contourArea(contour)
        x, y, w, h = cv2.boundingRect(contour)
        rect_area = w * h
        
        if rect_area == 0:
            return True
            
        extent = float(area) / rect_area
        
        # extent > 0.7 means it fills 70% of its bounding box, typical for a box
        # extent < 0.7 usually indicates deep cuts, huge dents or irregular shape
        return extent < 0.7
