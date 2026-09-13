import time

try:
    from .video_reader import VideoReader
    from .ascii_converter import AsciiConverter
    from .terminal_renderer import TerminalRenderer
    from .audio_player import AudioPlayer
    from .frame_cache import cache_dir_for, cache_is_valid, CacheWriter, CacheReader
except ImportError:
    from video_reader import VideoReader
    from ascii_converter import AsciiConverter
    from terminal_renderer import TerminalRenderer
    from audio_player import AudioPlayer
    from frame_cache import cache_dir_for, cache_is_valid, CacheWriter, CacheReader


class SyncPlayer:
    def __init__(self, video_path: str, out_width: int = None,
                 with_audio: bool = True, force_render: bool = False,
                 no_limit: bool = False, truecolor: bool = False):
        self.video_path = video_path
        self.out_width = out_width
        self.with_audio = with_audio
        self.force_render = force_render
        self.no_limit = no_limit
        self.truecolor = truecolor

    @staticmethod
    def _auto_width(video_width: int, video_height: int,
                     char_aspect: float = 2.0,
                     col_margin: int = 0, row_margin: int = 2) -> int:
        cols, rows = TerminalRenderer.terminal_size()
        max_cols = max(20, cols - col_margin)
        max_rows = max(10, rows - row_margin)

        width_from_cols = max_cols
        width_from_rows = int(max_rows * char_aspect * video_width / video_height)

        return max(20, min(width_from_cols, width_from_rows))

    @classmethod
    def _clamp_width(cls, requested_width: int, video_width: int,
                      video_height: int) -> int:
        max_fit = cls._auto_width(video_width, video_height)
        return min(requested_width, max_fit)

    def _render_cache(self, cache_dir: str, reader: VideoReader,
                       renderer: "TerminalRenderer") -> None:
        converter = AsciiConverter(out_width=self.out_width,
                                    truecolor=self.truecolor)

        print("Rendering ASCII frames to cache (first run only — "
              "later runs of this video reuse it and start instantly)...")

        writer = None
        i = 0
        for i, frame in enumerate(reader.frames()):
            chars, colors = converter.convert_resolved(frame)

            if writer is None:
                height, width = chars.shape
                writer = CacheWriter(cache_dir, self.video_path, reader.fps,
                                      reader.frame_count, self.out_width, height,
                                      truecolor=self.truecolor)

            writer.write_frame(chars, colors)

            if reader.frame_count:
                pct = int(100 * (i + 1) / reader.frame_count)
                print(f"\r  {i + 1}/{reader.frame_count} frames ({pct}%)",
                      end="", flush=True)
            else:
                print(f"\r  {i + 1} frames", end="", flush=True)

        if writer is None:
            writer = CacheWriter(cache_dir, self.video_path, reader.fps,
                                  0, self.out_width, 0, truecolor=self.truecolor)

        writer.close()
        renderer.clear_screen()

    def play(self):
        renderer = TerminalRenderer(truecolor=self.truecolor)
        renderer.clear_screen()

        with VideoReader(self.video_path) as reader:
            if self.out_width is None:
                self.out_width = self._auto_width(reader.width, reader.height)
            elif not self.no_limit:
                clamped = self._clamp_width(self.out_width, reader.width, reader.height)
                if clamped < self.out_width:
                    print(f"Note: --width {self.out_width} would produce a "
                          f"frame taller than your terminal, which breaks "
                          f"smooth playback. Using {clamped} instead — "
                          f"resize your terminal taller, use a smaller "
                          f"font, or pass --no-limit to force the exact "
                          f"width anyway.")
                    self.out_width = clamped

            cache_dir = cache_dir_for(self.video_path, self.out_width, self.truecolor)
            need_render = self.force_render or not cache_is_valid(
                cache_dir, self.video_path, reader.frame_count, self.out_width,
            )
            if need_render:
                self._render_cache(cache_dir, reader, renderer)

        cache = CacheReader(cache_dir)
        audio = AudioPlayer(self.video_path) if self.with_audio else None

        try:
            renderer.clear_screen()

            if audio:
                audio.play_async()

            fps = cache.fps
            total_frames = cache.frame_count
            start_time = time.perf_counter()
            last_shown_index = -1
            first_frame = True

            while True:
                elapsed = time.perf_counter() - start_time
                target_index = int(elapsed * fps)

                if target_index >= total_frames:
                    break

                if target_index != last_shown_index:
                    chars, colors = cache.get_frame(target_index)

                    if first_frame:
                        renderer.render(chars, colors)
                        first_frame = False
                    else:
                        renderer.render_diff(chars, colors)

                    last_shown_index = target_index
                else:
                    time.sleep(0.001)

        except KeyboardInterrupt:
            pass
        finally:
            renderer.close()
            if audio:
                audio.stop()
            cache.close()