# main.py: CLI entry point. Parses args, hands off to SyncPlayer.
# USAGE:
# python main.py video.mp4
# python main.py video.mp4 --width 260
# python main.py video.mp4 --no-audio
# python main.py video.mp4 --force-render
# python main.py video.mp4 --truecolor

import argparse,sys,os

# Handle relative imports for both python -m and direct runs
try:from .sync_player import SyncPlayer
except ImportError:sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));from sync_player import SyncPlayer

def build_arg_parser()->argparse.ArgumentParser:
 parser=argparse.ArgumentParser(prog="ascii_video_player",description="Play video as ASCII art in terminal with synced audio.")
 parser.add_argument("video_path",help="Path to video file (e.g. video.mp4)")
 parser.add_argument("--width","-w",type=int,default=None,help="ASCII canvas width. Defaults to terminal fit.")
 parser.add_argument("--no-audio",action="store_true",help="Disable audio playback.")
 parser.add_argument("--force-render",action="store_true",help="Re-render ASCII cache even if it exists.")
 parser.add_argument("--truecolor",action="store_true",help="Use 24-bit RGB color (slower, more accurate).")
 parser.add_argument("--no-limit",action="store_true",help="Use --width exactly, skip terminal-fit clamp.")
 return parser

def main(argv=None):
 parser=build_arg_parser()
 args=parser.parse_args(argv)
 player=SyncPlayer(
  video_path=args.video_path,
  out_width=args.width,
  with_audio=not args.no_audio,
  force_render=args.force_render,
  no_limit=args.no_limit,
  truecolor=args.truecolor)
 try:player.play()
 except(FileNotFoundError,EnvironmentError)as e:print(f"Error: {e}",file=sys.stderr);sys.exit(1)

if __name__=="__main__":main()