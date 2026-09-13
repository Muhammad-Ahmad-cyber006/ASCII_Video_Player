import cv2

class VideoReader:
 def __init__(self,path:str):
  self.path=path;self.cap=cv2.VideoCapture(path)
  if not self.cap.isOpened():raise FileNotFoundError(f"Could not open video file: {path}")
  self.fps=self.cap.get(cv2.CAP_PROP_FPS)or 25.0
  self.frame_count=int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
  self.width=int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
  self.height=int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
 def frames(self):
  while True:
   success,frame=self.cap.read()
   if not success:break
   yield frame
 def release(self):self.cap.release()
 def __enter__(self):return self
 def __exit__(self,exc_type,exc_val,exc_tb):self.release()