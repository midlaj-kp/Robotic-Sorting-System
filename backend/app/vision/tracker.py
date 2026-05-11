import math
from collections import OrderedDict

class CentroidTracker:
    def __init__(self, max_disappeared: int = 30, max_distance: int = 50):
        self.next_object_id = 1
        self.objects = OrderedDict()
        self.disappeared = OrderedDict()
        
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance

    def register(self, centroid):
        obj_id = f"obj_{self.next_object_id}"
        self.objects[obj_id] = centroid
        self.disappeared[obj_id] = 0
        self.next_object_id += 1

    def deregister(self, object_id):
        del self.objects[object_id]
        del self.disappeared[object_id]

    def update(self, rects):
        if len(rects) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return self.objects

        input_centroids = {}
        for (i, (x, y, w, h)) in enumerate(rects):
            cX = int((2 * x + w) / 2.0)
            cY = int((2 * y + h) / 2.0)
            input_centroids[i] = (cX, cY)

        if len(self.objects) == 0:
            for i in range(0, len(input_centroids)):
                self.register(input_centroids[i])
        else:
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())
            
            used_rows = set()
            used_cols = set()
            
            for (row, object_id) in enumerate(object_ids):
                # find closest input_centroid
                min_dist = float('inf')
                best_col = None
                
                for col in input_centroids:
                    if col in used_cols:
                        continue
                    (cX, cY) = input_centroids[col]
                    (oX, oY) = object_centroids[row]
                    d = math.hypot(cX - oX, cY - oY)
                    if d < min_dist:
                        min_dist = d
                        best_col = col
                
                if best_col is not None and min_dist < self.max_distance:
                    self.objects[object_id] = input_centroids[best_col]
                    self.disappeared[object_id] = 0
                    used_rows.add(row)
                    used_cols.add(best_col)
            
            # Unmatched objects
            unused_rows = set(range(0, len(object_centroids))).difference(used_rows)
            for row in unused_rows:
                object_id = object_ids[row]
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)

            # Unmatched input centroids (new objects)
            unused_cols = set(range(0, len(input_centroids))).difference(used_cols)
            for col in unused_cols:
                self.register(input_centroids[col])

        return self.objects
