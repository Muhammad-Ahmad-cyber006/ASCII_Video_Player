# ascii_converter.py: Converts video frame to resolved per-cell data (char + color).
import cv2, numpy as np

# 70-char brightness ramp (sparsest -> densest)
ASCII_CHARS=" .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
_CHAR_ORDINALS=np.array([ord(c) for c in ASCII_CHARS],dtype=np.uint8)
CACHE_FORMAT_VERSION=5 # Bumped for raw (chars, colors) arrays

# xterm 256-color cube levels
_CUBE_LEVELS=(0,95,135,175,215,255)
_LEVELS_ARR=np.array(_CUBE_LEVELS)
_CHANNEL_TO_LEVEL=np.array([int(np.argmin(np.abs(_LEVELS_ARR-v))) for v in range(256)],dtype=np.int32)

def _rgb_to_256_array(r:np.ndarray,g:np.ndarray,b:np.ndarray)->np.ndarray:
 r,g,b=r.astype(np.int32),g.astype(np.int32),b.astype(np.int32)
 is_gray=(np.abs(r-g)<10)&(np.abs(g-b)<10)&(np.abs(r-b)<10)
 r6,g6,b6=_CHANNEL_TO_LEVEL[r],_CHANNEL_TO_LEVEL[g],_CHANNEL_TO_LEVEL[b]
 cube_idx=16+36*r6+6*g6+b6
 n=np.clip(np.round((r-8)/10).astype(np.int32),0,23)
 gray_idx=232+n
 gray_idx=np.where(r<8,16,gray_idx)
 gray_idx=np.where(r>238,231,gray_idx)
 return np.where(is_gray,gray_idx,cube_idx).astype(np.uint8)

class AsciiConverter:
 def __init__(self,out_width:int=220,char_aspect:float=2.0,truecolor:bool=False):
     
  self.out_width=out_width;self.char_aspect=char_aspect;self.truecolor=truecolor
  
 def _resize_for_terminal(self,frame:np.ndarray)->np.ndarray:
     
  h,w=frame.shape[:2];new_w=self.out_width;new_h=max(1,int((h/w)*new_w/self.char_aspect))
  return cv2.resize(frame,(new_w,new_h),interpolation=cv2.INTER_AREA)

 def convert_resolved(self,frame_bgr:np.ndarray):
     
  small=self._resize_for_terminal(frame_bgr)
  rgb=cv2.cvtColor(small,cv2.COLOR_BGR2RGB)
  gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
  n_chars=len(ASCII_CHARS)
  char_indices=np.clip((gray.astype(np.float32)/255.0*n_chars).astype(np.int32),0,n_chars-1)
  chars=_CHAR_ORDINALS[char_indices]
  r,g,b=rgb[...,0],rgb[...,1],rgb[...,2]
  if self.truecolor:colors=(r.astype(np.uint32)<<16)|(g.astype(np.uint32)<<8)|b.astype(np.uint32)
  else:colors=_rgb_to_256_array(r,g,b)
  return chars,colors

 def convert(self,frame_bgr:np.ndarray)->str:
  chars,colors=self.convert_resolved(frame_bgr)
  height,width=chars.shape;lines=[]
  for y in range(height):
   parts=[];prev=None;row_chars=chars[y].tolist();row_colors=colors[y].tolist()
   for ch_ord,color in zip(row_chars,row_colors):
    if color!=prev:
     if self.truecolor:
      rr,gg,bb=(color>>16)&0xFF,(color>>8)&0xFF,color&0xFF
      parts.append(f"\x1b[38;2;{rr};{gg};{bb}m{chr(ch_ord)}")
     else:parts.append(f"\x1b[38;5;{color}m{chr(ch_ord)}")
     prev=color
    else:parts.append(chr(ch_ord))
   lines.append("".join(parts)+"\x1b[0m")
  return "\n".join(lines)
 frame_to_ascii=convert