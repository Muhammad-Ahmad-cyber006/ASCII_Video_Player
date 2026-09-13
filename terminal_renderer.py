import os,platform,sys,shutil,numpy as np

def _enable_windows_ansi_support():
 if platform.system()!="Windows":return
 try:
  import ctypes
  kernel32=ctypes.windll.kernel32
  STD_OUTPUT_HANDLE=-11;ENABLE_VIRTUAL_TERMINAL_PROCESSING=0x0004
  handle=kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
  mode=ctypes.c_uint32()
  if kernel32.GetConsoleMode(handle,ctypes.byref(mode)):kernel32.SetConsoleMode(handle,mode.value|ENABLE_VIRTUAL_TERMINAL_PROCESSING)
 except Exception:pass

def _encode_span(chars_row,colors_row,truecolor:bool)->str:
 parts=[];prev=None
 for ch_ord,color in zip(chars_row.tolist(),colors_row.tolist()):
  if color!=prev:
   if truecolor:
    r,g,b=(color>>16)&0xFF,(color>>8)&0xFF,color&0xFF
    parts.append(f"\x1b[38;2;{r};{g};{b}m{chr(ch_ord)}")
   else:parts.append(f"\x1b[38;5;{color}m{chr(ch_ord)}")
   prev=color
  else:parts.append(chr(ch_ord))
 return"".join(parts)

class TerminalRenderer:
 def __init__(self,truecolor:bool=False):
  self.truecolor=truecolor;_enable_windows_ansi_support();self._hide_cursor()
  self._prev_chars=None;self._prev_colors=None
 def _hide_cursor(self):sys.stdout.write("\x1b[?25l");sys.stdout.flush()
 def _show_cursor(self):sys.stdout.write("\x1b[?25h");sys.stdout.flush()
 def clear_screen(self):
  sys.stdout.write("\x1b[2J\x1b[3J\x1b[H");sys.stdout.flush()
  self._prev_chars=None;self._prev_colors=None
 def render(self,chars:np.ndarray,colors:np.ndarray):
  height=chars.shape[0]
  lines=[_encode_span(chars[y],colors[y],self.truecolor)+"\x1b[0m"for y in range(height)]
  sys.stdout.write("\x1b[H"+"\n".join(lines));sys.stdout.flush()
  self._prev_chars=chars;self._prev_colors=colors
 def render_diff(self,chars:np.ndarray,colors:np.ndarray):
  if self._prev_chars is None or self._prev_chars.shape!=chars.shape:self.render(chars,colors);return
  diff_mask=(chars!=self._prev_chars)|(colors!=self._prev_colors)
  if not diff_mask.any():self._prev_chars=chars;self._prev_colors=colors;return
  row_has_diff=diff_mask.any(axis=1);changed_rows=np.flatnonzero(row_has_diff)
  parts=[]
  for row_index in changed_rows:
   mask_row=diff_mask[row_index]
   first=int(mask_row.argmax());last=int(len(mask_row)-1-mask_row[::-1].argmax())
   span_text=_encode_span(chars[row_index,first:last+1],colors[row_index,first:last+1],self.truecolor)
   parts.append(f"\x1b[{row_index+1};{first+1}H"+span_text)
  self._prev_chars=chars;self._prev_colors=colors
  sys.stdout.write("".join(parts));sys.stdout.flush()
 @staticmethod
 def terminal_size():
  try:size=os.get_terminal_size(sys.stdout.fileno());return size.columns,size.lines
  except(OSError,ValueError,AttributeError):pass
  cols,rows=shutil.get_terminal_size(fallback=(120,40));return cols,rows
 def close(self):self._show_cursor()