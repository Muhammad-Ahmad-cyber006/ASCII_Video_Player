import hashlib,json,os,threading,numpy as np

try:from .ascii_converter import CACHE_FORMAT_VERSION
except ImportError:from ascii_converter import CACHE_FORMAT_VERSION

def cache_dir_for(video_path:str,width:int,truecolor:bool=False)->str:
 video_dir=os.path.dirname(os.path.abspath(video_path))
 stem=os.path.splitext(os.path.basename(video_path))[0]
 suffix="_tc"if truecolor else"";return os.path.join(video_dir,f"{stem}_ascii_cache_{width}{suffix}")

def _video_fingerprint(video_path:str)->str:
 stat=os.stat(video_path);raw=f"{stat.st_size}-{stat.st_mtime}".encode("utf-8")
 return hashlib.sha1(raw).hexdigest()[:16]

def _frame_filename(index:int)->str:return f"{index+1:06d}.bin"

def cache_is_valid(cache_dir:str,video_path:str,frame_count:int,width:int)->bool:
 meta_path=os.path.join(cache_dir,"metadata.json")
 if not os.path.exists(meta_path):return False
 try:
  with open(meta_path,"r",encoding="utf-8")as f:meta=json.load(f)
 except(json.JSONDecodeError,OSError):return False
 return(meta.get("fingerprint")==_video_fingerprint(video_path)
        and meta.get("width")==width
        and meta.get("frame_count")==frame_count
        and meta.get("format_version")==CACHE_FORMAT_VERSION)

class CacheWriter:
 def __init__(self,cache_dir:str,video_path:str,fps:float,frame_count:int,width:int,height:int,truecolor:bool=False):
  self.cache_dir=cache_dir;self.frames_dir=os.path.join(cache_dir,"frames")
  os.makedirs(self.frames_dir,exist_ok=True)
  self._meta_path=os.path.join(cache_dir,"metadata.json")
  self._meta={"fingerprint":_video_fingerprint(video_path),"fps":fps,"frame_count":frame_count,
             "width":width,"height":height,"truecolor":truecolor,"format_version":CACHE_FORMAT_VERSION}
  self._next_index=0
 def write_frame(self,chars:np.ndarray,colors:np.ndarray):
  path=os.path.join(self.frames_dir,_frame_filename(self._next_index))
  with open(path,"wb")as f:f.write(chars.tobytes());f.write(colors.tobytes())
  self._next_index+=1
 def close(self):
  with open(self._meta_path,"w",encoding="utf-8")as f:json.dump(self._meta,f)

class CacheReader:
 def __init__(self,cache_dir:str,read_ahead:int=24):
  self.cache_dir=cache_dir;self.frames_dir=os.path.join(cache_dir,"frames")
  with open(os.path.join(cache_dir,"metadata.json"),"r",encoding="utf-8")as f:self.meta=json.load(f)
  self.height=self.meta["height"];self.width=self.meta["width"]
  self.truecolor=self.meta.get("truecolor",False)
  self._color_dtype=np.uint32 if self.truecolor else np.uint8
  self._hw=self.height*self.width
  self._read_ahead=read_ahead;self._buffer={};self._lock=threading.Lock()
  self._next_to_prefetch=0;self._last_requested=-1;self._stop=threading.Event()
  self._thread=threading.Thread(target=self._prefetch_loop,daemon=True);self._thread.start()
 def _read_frame_from_disk(self,index:int):
  path=os.path.join(self.frames_dir,_frame_filename(index))
  raw=np.fromfile(path,dtype=np.uint8)
  chars=raw[:self._hw].reshape(self.height,self.width)
  color_bytes=raw[self._hw:]
  if self.truecolor:colors=color_bytes.view(np.uint32).reshape(self.height,self.width)
  else:colors=color_bytes.reshape(self.height,self.width)
  return chars,colors
 def _prefetch_loop(self):
  total=self.frame_count
  while not self._stop.is_set():
   with self._lock:
    target=self._last_requested+self._read_ahead
    need_more=(self._next_to_prefetch<=target
               and self._next_to_prefetch<total
               and self._next_to_prefetch not in self._buffer)
   if not need_more:self._stop.wait(0.005);continue
   idx=self._next_to_prefetch
   try:frame=self._read_frame_from_disk(idx)
   except OSError:break
   with self._lock:
    self._buffer[idx]=frame;self._next_to_prefetch=idx+1
    stale=[i for i in self._buffer if i<self._last_requested]
    for i in stale:del self._buffer[i]
 @property
 def fps(self)->float:return self.meta["fps"]
 @property
 def frame_count(self)->int:return self.meta["frame_count"]
 def get_frame(self,index:int):
  with self._lock:
   self._last_requested=index;cached=self._buffer.pop(index,None)
   if cached is not None:return cached
   if index>self._next_to_prefetch:self._next_to_prefetch=index
  return self._read_frame_from_disk(index)
 def close(self):
  self._stop.set();self._thread.join(timeout=1.0)