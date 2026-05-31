import os
import platform
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import tempfile
import shutil
import time
import sys

from PIL import Image, ImageDraw, ImageFont, ImageTk



ASCII_CHARS_LIGHT = " .:-=+*#%@"
ASCII_CHARS_MEDIUM = r" .'`^\",:;Il!i><~+_-?][}{1)(|\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
ASCII_CHARS_HEAVY = "@#W&8%B$?*oahkbdpqwmZ0OQLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:'\"^`. "
ASCII_CHARS_COMPUTER_SCRASHER = "@#W&8%B$?*oahkbdpqwmZ0OQLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:'\"^`.@#%?*!;:.,<>/|[]{}()1Il"
ASCII_CHARS = ASCII_CHARS_MEDIUM

COLOR_PALETTES = {
    "grayscale": [(i, i, i) for i in range(256)],
    "warm": [(255, int(255 * i / 255), 0) for i in range(256)],
    "cool": [(0, int(255 * i / 255), 255) for i in range(256)],
    "rainbow": [(255, 0, 0) if i < 43 else (255, 165, 0) if i < 86 else (255, 255, 0) if i < 129 else (0, 128, 0) if i < 172 else (0, 0, 255) if i < 215 else (75, 0, 130) for i in range(256)],
    "sepia": [
        (
            min(255, int(i * 0.8 + 60)),
            min(255, int(i * 0.55 + 30)),
            min(255, int(i * 0.3))
        )
        for i in range(256)
    ],
    "ocean": [
        (
            int(i * 0.2),
            min(255, int(90 + i * 0.6)),
            min(255, int(160 + i * 0.35))
        )
        for i in range(256)
    ],
    "sunset": [
        (
            min(255, int(220 + i * 0.14)),
            min(255, int(90 + i * 0.4)),
            min(255, int(40 + i * 0.16))
        )
        for i in range(256)
    ],
    "neon": [
        (
            min(255, int(255 * (i / 255)**0.5)),
            min(255, int(255 * ((255 - i) / 255)**0.7)),
            min(255, int(255 * (0.5 + 0.5 * (i / 255))))
        )
        for i in range(256)
    ],
}


def load_image(path):
    return Image.open(path).convert("RGB")


def scale_to_ascii_size(width, height, scale, char_ratio=2.0):
    new_width = max(16, int(width * scale))
    new_height = max(16, int(height * scale / char_ratio))
    return new_width, new_height


def get_brightness(r, g, b):
    value = 0.2126 * r + 0.7152 * g + 0.0722 * b
    normalized = value / 255.0
    gamma = 1.05
    return int(min(255, (normalized ** gamma) * 255))


def pixel_to_char(brightness, charset=ASCII_CHARS):
    index = int(brightness / 255 * (len(charset) - 1))
    return charset[index]


def get_font_char_size(font, char="A"):
    if hasattr(font, "getbbox"):
        bbox = font.getbbox(char)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    image = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(image)
    bbox = draw.textbbox((0, 0), char, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def get_color_for_brightness(brightness, palette_name="grayscale"):
    palette = COLOR_PALETTES.get(palette_name, COLOR_PALETTES["grayscale"])
    index = int(brightness / 255 * (len(palette) - 1))
    return palette[index]


def clamp_scale_for_charset(scale, charset):
    if charset == ASCII_CHARS_HEAVY:
        return min(scale, 0.22)
    return scale


def select_charset(charset_key):
    if charset_key == "light":
        return ASCII_CHARS_LIGHT
    if charset_key == "medium":
        return ASCII_CHARS_MEDIUM
    if charset_key == "heavy":
        return ASCII_CHARS_HEAVY
    if charset_key == "computer scrasher":
        return ASCII_CHARS_COMPUTER_SCRASHER
    return ASCII_CHARS_MEDIUM


def ensure_cv2():
    import cv2
    return cv2


def ensure_numpy():
    import numpy as np
    return np


def image_to_ascii_image(image, scale=0.12, color=False, charset=ASCII_CHARS, palette="grayscale"):
    font = ImageFont.load_default()
    char_width, char_height = get_font_char_size(font)
    char_ratio = float(char_height) / float(char_width) if char_width else 2.0
    new_width, new_height = scale_to_ascii_size(image.width, image.height, scale, char_ratio=char_ratio)
    small = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    ascii_image = Image.new("RGB", (new_width * char_width, new_height * char_height), "white")
    draw = ImageDraw.Draw(ascii_image)

    lines = []
    for y in range(new_height):
        row_chars = []
        for x in range(new_width):
            r, g, b = small.getpixel((x, y))
            brightness = get_brightness(r, g, b)
            char = pixel_to_char(brightness, charset)
            if color:
                if palette == "original":
                    color_fill = (r, g, b)
                else:
                    color_fill = get_color_for_brightness(brightness, palette)
            else:
                color_fill = (0, 0, 0)
            draw.text((x * char_width, y * char_height), char, fill=color_fill, font=font)
            row_chars.append(char)
        lines.append("".join(row_chars))

    return ascii_image, "\n".join(lines)


def save_ascii_text(image, output_path, scale=0.12, charset=ASCII_CHARS):
    _, ascii_text = image_to_ascii_image(image, scale=scale, color=False, charset=charset)
    with open(output_path, "w", encoding="utf-8") as text_file:
        text_file.write(ascii_text)


def extract_audio(input_video, output_audio):
    """Extract audio from video using ffmpeg."""
    try:
        cmd = [
            "ffmpeg", "-i", input_video, "-q:a", "9", "-n",
            "-vn", output_audio
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=300)
        return True
    except Exception:
        return False


def extract_audio_wav(input_video, output_audio):
    """Extract audio from video into WAV for playback."""
    try:
        cmd = [
            "ffmpeg", "-y", "-i", input_video, "-vn", "-acodec", "pcm_s16le",
            "-ar", "44100", "-ac", "2", output_audio
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=300)
        return True
    except Exception:
        return False


def remux_audio_to_video(video_path, audio_path, output_path):
    """Add audio back to video using ffmpeg."""
    try:
        cmd = [
            "ffmpeg", "-i", video_path, "-i", audio_path, "-c:v", "copy",
            "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0", "-n", output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=300)
        return True
    except Exception:
        return False


def convert_video_to_target_format(input_path, output_path, output_ext):
    output_ext = output_ext.lower()
    try:
        if output_ext == "mp4":
            shutil.copyfile(input_path, output_path)
            return True

        if not shutil.which("ffmpeg"):
            return False

        cmd = ["ffmpeg", "-i", input_path, "-c:v", "copy"]
        if output_ext == "avi":
            cmd += ["-c:a", "mp3"]
        else:
            cmd += ["-c:a", "copy"]
        cmd += ["-y", output_path]
        subprocess.run(cmd, capture_output=True, check=True, timeout=300)
        return True
    except Exception:
        return False


def video_to_ascii_video(input_path, output_path, scale=0.12, color=False, charset=ASCII_CHARS, palette="grayscale", status_callback=None):
    cv2 = ensure_cv2()
    np = ensure_numpy()
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened() and isinstance(input_path, str):
        cap.release()
        cap = cv2.VideoCapture(input_path.encode("utf-8"))
    if not cap.isOpened():
        raise RuntimeError("Cannot open video file. Try moving the file to a path without special characters or select a different file.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    font = ImageFont.load_default()
    char_width, char_height = get_font_char_size(font)
    # Ensure sensible non-zero char sizes
    if not char_width or not char_height:
        # Fallback approximate default for default font
        char_width, char_height = 6, 10

    char_ratio = float(char_height) / float(char_width) if char_width else 2.0
    new_width, new_height = scale_to_ascii_size(width, height, scale, char_ratio=char_ratio)
    frame_width = new_width * char_width
    frame_height = new_height * char_height

    # Make frame dimensions even (some codecs require even dims)
    if frame_width % 2 != 0:
        frame_width += 1
    if frame_height % 2 != 0:
        frame_height += 1

    # Try multiple fourccs in case default fails on user's system
    fourcc_candidates = ["mp4v", "XVID", "avc1", "H264"]
    writer = None
    for code in fourcc_candidates:
        try:
            fourcc = cv2.VideoWriter_fourcc(*code)
            writer = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
            if writer.isOpened():
                if status_callback:
                    status_callback(f"Using codec: {code}")
                break
            else:
                # release and try next
                try:
                    writer.release()
                except Exception:
                    pass
                writer = None
        except Exception:
            writer = None

    if writer is None or not writer.isOpened():
        cap.release()
        raise RuntimeError("Failed to open video writer with available codecs on this system.")
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    processed = 0

    try:
        while True:
            success, frame = cap.read()
            if not success:
                break

            try:
                pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                ascii_frame, _ = image_to_ascii_image(pil_frame, scale=scale, color=color, charset=charset, palette=palette)
                arr = np.array(ascii_frame)
                # Ensure array has correct shape and dtype
                if arr.dtype != np.uint8:
                    arr = arr.astype(np.uint8)
                bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
                # Resize to expected frame size if mismatched
                if (bgr.shape[1], bgr.shape[0]) != (frame_width, frame_height):
                    bgr = cv2.resize(bgr, (frame_width, frame_height), interpolation=cv2.INTER_AREA)
                writer.write(bgr)
            except Exception as e:
                # Skip problematic frame but keep going
                if status_callback:
                    status_callback(f"Skipping frame {processed+1} due to error: {e}")

            processed += 1
            if status_callback and frame_count:
                progress = int(processed / frame_count * 100) if frame_count else 0
                status_callback(f"Converting video: {progress}% ({processed}/{frame_count})")
    finally:
        try:
            cap.release()
        except Exception:
            pass
        try:
            writer.release()
        except Exception:
            pass

    cap.release()
    writer.release()


class AsciiTranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("zib's convertor")
        self.root.geometry("1500x850")
        self.root.resizable(True, True)

        self.current_path = None
        self.current_image = None
        self.output_image = None
        self.video_cap = None
        self.video_playing = False
        self.video_paused = False
        self.video_frame_idx = 0
        self.video_muted = False
        self.video_frames = []
        self.video_total_frames = 0
        self.video_fps = 24
        self.video_last_frame_time = 0
        self.converted_video_path = None
        self.converted_video_extension = None
        self.preview_canvas_image_id = None
        self.progress_var = tk.DoubleVar(value=0)
        self.convert_button = None
        self.save_ascii_button = None
        self.save_output_button = None
        self.save_converted_button = None
        self.audio_button = None
        self.audio_playing = False
        self.audio_wave_path = None
        self.audio_process = None

        self.build_ui()

    def build_ui(self):
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_panel = tk.Frame(main_frame, width=300, bg="#f0f0f0")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        left_panel.pack_propagate(False)

        # Title with optional converter image to the left
        title_frame = tk.Frame(left_panel, bg="#f0f0f0")
        title_frame.pack(pady=(0, 12))
        try:
            conv_path = os.path.join(os.path.dirname(__file__), "Converter.png")
            if os.path.exists(conv_path):
                conv_img = Image.open(conv_path).convert("RGBA")
                conv_img.thumbnail((40, 40), Image.Resampling.LANCZOS)
                self.title_icon = ImageTk.PhotoImage(conv_img)
                icon_lbl = tk.Label(title_frame, image=self.title_icon, bg="#f0f0f0")
                icon_lbl.pack(side=tk.LEFT, padx=(0, 8))
        except Exception:
            pass

        try:
            tab_icon_path = os.path.join(os.path.dirname(__file__), "Tabimage.ico")
            if os.path.exists(tab_icon_path):
                try:
                    self.root.iconbitmap(tab_icon_path)
                except Exception:
                    pass
                try:
                    icon_image = ImageTk.PhotoImage(Image.open(tab_icon_path))
                    self.root.iconphoto(True, icon_image)
                    self.root._icon_image = icon_image
                except Exception:
                    pass
        except Exception:
            pass

        tk.Label(title_frame, text="zib's convertor", font=("Segoe UI", 14, "bold"), bg="#f0f0f0").pack(side=tk.LEFT)

        tk.Button(left_panel, text="Open Image", width=26, command=self.open_image).pack(pady=4)
        tk.Button(left_panel, text="Open Video", width=26, command=self.open_video).pack(pady=4)

        tk.Label(left_panel, text="Settings", font=("Segoe UI", 10, "bold"), bg="#f0f0f0").pack(pady=(12, 8), anchor="w")

        tk.Label(left_panel, text="Scale factor:", bg="#f0f0f0").pack(anchor="w", pady=(4, 0))
        self.scale_var = tk.DoubleVar(value=0.11)
        tk.Scale(left_panel, variable=self.scale_var, from_=0.04, to=0.24, resolution=0.01, orient=tk.HORIZONTAL, length=240).pack(fill=tk.X)

        tk.Label(left_panel, text="ASCII Charset:", bg="#f0f0f0").pack(anchor="w", pady=(8, 0))
        self.charset_var = tk.StringVar(value="medium")
        for opt in ["light", "medium", "heavy", "computer scrasher"]:
            tk.Radiobutton(left_panel, text=opt, variable=self.charset_var, value=opt, bg="#f0f0f0").pack(anchor="w")

        tk.Label(left_panel, text="Color Palette:", bg="#f0f0f0").pack(anchor="w", pady=(8, 0))
        self.palette_var = tk.StringVar(value="original")
        tk.OptionMenu(
            left_panel,
            self.palette_var,
            "grayscale",
            "warm",
            "cool",
            "rainbow",
            "sepia",
            "ocean",
            "sunset",
            "neon",
            "original"
        ).pack(fill=tk.X)

        tk.Label(left_panel, text="Image Format:", bg="#f0f0f0").pack(anchor="w", pady=(8, 0))
        self.image_format_var = tk.StringVar(value="png")
        tk.OptionMenu(left_panel, self.image_format_var, "png", "jpg").pack(fill=tk.X)

        tk.Label(left_panel, text="Video Format:", bg="#f0f0f0").pack(anchor="w", pady=(8, 0))
        self.video_format_var = tk.StringVar(value="mp4")
        tk.OptionMenu(left_panel, self.video_format_var, "mp4", "avi").pack(fill=tk.X)

        self.color_var = tk.BooleanVar(value=True)
        tk.Checkbutton(left_panel, text="Color output", variable=self.color_var, bg="#f0f0f0").pack(anchor="w", pady=(8, 4))

        self.preserve_audio_var = tk.BooleanVar(value=True)
        tk.Checkbutton(left_panel, text="Preserve audio", variable=self.preserve_audio_var, bg="#f0f0f0").pack(anchor="w", pady=2)

        self.convert_button = tk.Button(left_panel, text="Convert", width=26, command=self.convert_current, bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"))
        self.convert_button.pack(pady=(12, 4))

        self.save_ascii_button = tk.Button(left_panel, text="Save ASCII text", width=26, command=self.save_text_file)
        self.save_ascii_button.pack(pady=2)
        self.save_output_button = tk.Button(left_panel, text="Save output", width=26, command=self.save_output_file)
        self.save_output_button.pack(pady=2)
        self.save_converted_button = tk.Button(left_panel, text="Save converted video", width=26, command=self.save_converted_video, state=tk.DISABLED)
        self.save_converted_button.pack(pady=2)

        tk.Label(left_panel, text="Conversion progress:", bg="#f0f0f0").pack(anchor="w", pady=(12, 2))
        self.progress_bar = ttk.Progressbar(left_panel, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))

        right_panel = tk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        top_row = tk.Frame(right_panel)
        top_row.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        preview_frame = tk.LabelFrame(top_row, text="Original File", font=("Segoe UI", 10, "bold"))
        preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.preview_canvas = tk.Canvas(preview_frame, bg="#efefef", highlightthickness=0)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)

        self.video_controls_frame = tk.Frame(preview_frame, bg="white")
        self.video_controls_frame.pack(fill=tk.X, pady=4)
        self.video_controls_frame.pack_forget()

        tk.Button(self.video_controls_frame, text="▶ Play", width=8, command=self.play_video).pack(side=tk.LEFT, padx=2)
        tk.Button(self.video_controls_frame, text="⏸ Pause", width=8, command=self.pause_video).pack(side=tk.LEFT, padx=2)
        self.audio_button = tk.Button(self.video_controls_frame, text="🔊 Audio", width=10, command=self.toggle_audio)
        self.audio_button.pack(side=tk.LEFT, padx=2)
        self.mute_label = tk.Label(self.video_controls_frame, text="(Off)", width=8)
        self.mute_label.pack(side=tk.LEFT, padx=2)
        self.frame_label = tk.Label(self.video_controls_frame, text="0/0")
        self.frame_label.pack(side=tk.LEFT, padx=20)

        output_frame = tk.LabelFrame(top_row, text="ASCII Output", font=("Segoe UI", 10, "bold"))
        output_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        self.output_canvas = tk.Canvas(output_frame, bg="#efefef", highlightthickness=0)
        self.output_canvas.pack(fill=tk.BOTH, expand=True)

        self.text_box = tk.Text(right_panel, width=100, height=8, wrap=tk.WORD, font=("Courier", 8))
        self.text_box.pack(fill=tk.BOTH, expand=False)

        self.status_label = tk.Label(self.root, text="Ready", anchor="w", relief=tk.SUNKEN)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=4)

    def set_controls_enabled(self, enabled: bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        if self.convert_button:
            self.convert_button.config(state=state)
        if self.save_ascii_button:
            self.save_ascii_button.config(state=state)
        if self.save_output_button:
            self.save_output_button.config(state=state)
        if self.save_converted_button:
            self.save_converted_button.config(state=state if self.converted_video_path else tk.DISABLED)
        if self.audio_button:
            self.audio_button.config(state=state)

    def update_progress(self, value: float):
        self.progress_var.set(value)
        self.root.update_idletasks()

    def update_status(self, message):
        self.status_label.config(text=message)
        self.root.update_idletasks()
        if message.startswith("Converting video:"):
            try:
                percent = int(message.split("%", 1)[0].split()[-1])
                self.update_progress(percent)
            except Exception:
                pass
        elif message.startswith("Preparing") or message.startswith("Saving"):
            self.update_progress(0)
        elif message.startswith("✓") or message.startswith("Error"):
            self.update_progress(100 if message.startswith("✓") else 0)

    def play_audio(self):
        if not self.current_path:
            messagebox.showwarning("No audio", "Open a video first.")
            return

        if not shutil.which("ffmpeg"):
            messagebox.showerror("Missing ffmpeg", "FFmpeg is required for audio playback.")
            return

        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
        if not extract_audio_wav(self.current_path, temp_audio):
            try:
                os.remove(temp_audio)
            except Exception:
                pass
            messagebox.showerror("Audio error", "Could not extract audio from the video.")
            return

        self.audio_wave_path = temp_audio
        self.audio_playing = True
        self.mute_label.config(text="(On)")
        self.audio_button.config(text="🔇 Stop")
        self.update_status("Playing audio...")

        if platform.system() == "Windows":
            try:
                import winsound
                winsound.PlaySound(self.audio_wave_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception:
                messagebox.showerror("Audio error", "Could not play audio on this system.")
                self.stop_audio()
        elif shutil.which("ffplay"):
            self.audio_process = subprocess.Popen(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", self.audio_wave_path])
        else:
            messagebox.showerror("Audio error", "Audio playback is not supported on this system.")
            self.stop_audio()

    def stop_audio(self):
        if platform.system() == "Windows":
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
        if self.audio_process:
            try:
                self.audio_process.terminate()
            except Exception:
                pass
            self.audio_process = None
        if self.audio_wave_path and os.path.exists(self.audio_wave_path):
            try:
                os.remove(self.audio_wave_path)
            except Exception:
                pass
        self.audio_playing = False
        self.audio_wave_path = None
        self.mute_label.config(text="(Off)")
        self.audio_button.config(text="🔊 Audio")
        self.update_status("Audio stopped.")

    def toggle_audio(self):
        if self.audio_playing:
            self.stop_audio()
        else:
            self.play_audio()

    def open_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*")]
        )
        if not path:
            return
        self.current_path = path
        self.current_image = load_image(path)
        self.output_image = None
        self.video_cap = None
        self.video_playing = False
        self.converted_video_path = None
        self.converted_video_extension = None
        self.text_box.delete("1.0", tk.END)
        self.video_controls_frame.pack_forget()
        if self.save_converted_button:
            self.save_converted_button.config(state=tk.DISABLED)
        self.show_preview_image(self.current_image)
        self.update_progress(0)
        self.update_status(f"Loaded image: {os.path.basename(path)}")

    def open_video(self):
        path = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.mov *.avi *.mkv"), ("All files", "*")]
        )
        if not path:
            return
        self.current_path = path
        self.current_image = None
        self.output_image = None
        self.video_playing = False
        self.video_cap = None
        self.converted_video_path = None
        self.converted_video_extension = None
        self.video_frames = []
        self.text_box.delete("1.0", tk.END)
        self.video_controls_frame.pack(fill=tk.X, pady=4)
        if self.save_converted_button:
            self.save_converted_button.config(state=tk.DISABLED)
        self.update_progress(0)

        cv2 = ensure_cv2()
        cap = cv2.VideoCapture(path)
        if not cap.isOpened() and isinstance(path, str):
            try:
                cap.release()
            except Exception:
                pass
            cap = cv2.VideoCapture(path.encode("utf-8"))
        if cap.isOpened():
            self.video_fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
            self.video_total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            success, frame = cap.read()
            cap.release()
            if success:
                preview_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                self.show_preview_image(preview_image)
                self.frame_label.config(text=f"0/{self.video_total_frames}")
                self.update_status(f"Loaded video: {os.path.basename(path)}")
                return

        self.update_status(f"Loaded video: {os.path.basename(path)}")
        self.preview_canvas.delete("all")
        self.preview_canvas.create_text(200, 100, text="Video loaded.\nConvert to generate ASCII.", font=("Segoe UI", 12))

    def show_preview_image(self, image):
        self.show_on_canvas(self.preview_canvas, image, max_size=450)

    def show_output_image(self, image):
        self.show_on_canvas(self.output_canvas, image, max_size=450)

    def show_on_canvas(self, canvas, pil_image, max_size=450):
        """Display a PIL image centered on a Canvas while maintaining aspect ratio."""
        img_copy = pil_image.copy()
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()

        if canvas_width < 100 or canvas_height < 100:
            canvas_width = max_size
            canvas_height = max_size

        img_width = img_copy.width
        img_height = img_copy.height

        scale_w = canvas_width / img_width
        scale_h = canvas_height / img_height
        scale = min(scale_w, scale_h, 1.0)

        new_width = int(img_width * scale)
        new_height = int(img_height * scale)

        if new_width > 0 and new_height > 0:
            img_copy = img_copy.resize((new_width, new_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img_copy)
            if getattr(canvas, "image_id", None) is None:
                canvas.image_id = canvas.create_image(canvas_width // 2, canvas_height // 2, image=photo)
            else:
                canvas.itemconfig(canvas.image_id, image=photo)
            canvas.image = photo

    def convert_current(self):
        if not self.current_path:
            messagebox.showwarning("No file", "Open an image or video first.")
            return
        if self.current_image is not None:
            self.convert_image()
        else:
            self.convert_video()

    def convert_image(self):
        self.set_controls_enabled(False)
        scale = self.scale_var.get()
        color = self.color_var.get()
        charset_key = self.charset_var.get()
        palette = self.palette_var.get()
        charset = select_charset(charset_key)
        scale = clamp_scale_for_charset(scale, charset)

        self.update_status("Converting image to ASCII...")
        try:
            ascii_img, ascii_text = image_to_ascii_image(self.current_image, scale=scale, color=color, charset=charset, palette=palette)
            self.output_image = ascii_img
            self.show_output_image(ascii_img)
            self.text_box.delete("1.0", tk.END)
            self.text_box.insert(tk.END, ascii_text[:3000])
            self.update_status("✓ Image converted successfully.")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to convert image:\n{exc}")
            self.update_status("Error converting image.")
        finally:
            self.set_controls_enabled(True)

    def convert_video(self):
        scale = self.scale_var.get()
        color = self.color_var.get()
        charset_key = self.charset_var.get()
        palette = self.palette_var.get()
        preserve_audio = self.preserve_audio_var.get()
        charset = select_charset(charset_key)
        scale = clamp_scale_for_charset(scale, charset)

        if not self.current_path:
            return

        self.set_controls_enabled(False)

        def task():
            try:
                self.update_status("Preparing video conversion...")
                temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name

                video_to_ascii_video(
                    self.current_path,
                    temp_output,
                    scale=scale,
                    color=color,
                    charset=charset,
                    palette=palette,
                    status_callback=self.update_status,
                )

                if preserve_audio and shutil.which("ffmpeg"):
                    self.update_status("Processing audio...")
                    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".aac").name
                    if extract_audio(self.current_path, temp_audio):
                        final_output = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                        if remux_audio_to_video(temp_output, temp_audio, final_output):
                            try:
                                os.remove(temp_output)
                            except OSError:
                                pass
                            try:
                                os.remove(temp_audio)
                            except OSError:
                                pass
                            temp_output = final_output

                self.converted_video_path = temp_output
                self.converted_video_extension = "mp4"
                self.output_image = None
                self.preview_canvas.delete("all")
                self.preview_canvas.create_text(200, 100, text="Video converted.\nSave to export.", font=("Segoe UI", 12))
                if self.save_converted_button:
                    self.save_converted_button.config(state=tk.NORMAL)
                self.update_status(f"✓ Video converted, ready to save.")
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to convert video:\n{exc}")
                self.update_status("Error converting video.")
            finally:
                self.set_controls_enabled(True)

        thread = threading.Thread(target=task, daemon=True)
        thread.start()

    def close_video_capture(self):
        if self.video_cap is not None:
            try:
                self.video_cap.release()
            except Exception:
                pass
            self.video_cap = None

    def prepare_video_playback(self):
        cv2 = ensure_cv2()
        self.close_video_capture()
        self.video_cap = cv2.VideoCapture(self.current_path)
        if not self.video_cap.isOpened():
            self.video_cap = None
            return False

        self.video_fps = self.video_cap.get(cv2.CAP_PROP_FPS) or 24.0
        self.video_total_frames = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self.video_frame_idx = 0
        self.frame_label.config(text=f"0/{self.video_total_frames}")
        return True

    def play_video(self):
        if not self.current_path or self.current_image is not None:
            return

        if not self.prepare_video_playback():
            messagebox.showerror("Error", "Could not open video for playback.")
            return

        self.video_playing = True
        self.video_paused = False
        self.video_last_frame_time = time.time()
        self.play_video_frame()

    def play_video_frame(self):
        if not self.video_playing or self.video_cap is None:
            return

        if self.video_paused:
            self.root.after(100, self.play_video_frame)
            return

        current_time = time.time()
        frame_duration = 1.0 / self.video_fps
        elapsed = current_time - self.video_last_frame_time

        if elapsed >= frame_duration:
            success, frame = self.video_cap.read()
            if not success:
                self.video_playing = False
                self.update_status("Video playback finished.")
                self.close_video_capture()
                return

            cv2 = ensure_cv2()
            canvas_width = self.preview_canvas.winfo_width() or 450
            canvas_height = self.preview_canvas.winfo_height() or 450
            if canvas_width > 0 and canvas_height > 0:
                frame = cv2.resize(frame, (canvas_width, canvas_height), interpolation=cv2.INTER_AREA)
            pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            self.show_preview_image(pil_frame)
            self.video_frame_idx += 1
            self.frame_label.config(text=f"{self.video_frame_idx}/{self.video_total_frames}")
            self.video_last_frame_time = current_time

        self.root.after(50, self.play_video_frame)

    def pause_video(self):
        self.video_paused = True
        self.update_status("⏸ Video paused")

    def toggle_mute(self):
        self.video_muted = not self.video_muted
        self.mute_label.config(text="(No audio)")
        self.update_status("🔊 Audio preview is not supported.")

    def save_text_file(self):
        if self.current_image is None:
            messagebox.showwarning("No image loaded", "Open an image first to save ASCII text.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text file", "*.txt")])
        if not path:
            return
        charset_key = self.charset_var.get()
        charset = select_charset(charset_key)
        save_ascii_text(self.current_image, path, scale=clamp_scale_for_charset(self.scale_var.get(), charset), charset=charset)
        self.update_status(f"✓ Saved ASCII text to {os.path.basename(path)}")

    def save_output_file(self):
        if self.current_image is not None and self.output_image is not None:
            fmt = self.image_format_var.get()
            ext = fmt
            path = filedialog.asksaveasfilename(defaultextension=f".{ext}", filetypes=[(f"{ext.upper()} image", f"*.{ext}")])
            if not path:
                return
            self.output_image.save(path, format=ext.upper() if ext == "jpg" else "PNG")
            self.update_status(f"✓ Saved image to {os.path.basename(path)}")
        elif self.current_image is None and self.current_path:
            fmt = self.video_format_var.get()
            ext = fmt
            path = filedialog.asksaveasfilename(defaultextension=f".{ext}", filetypes=[(f"{ext.upper()} video", f"*.{ext}")])
            if not path:
                return
            self.set_controls_enabled(False)
            self.update_status("Saving ASCII video... This may take a moment.")
            try:
                if self.converted_video_path and os.path.exists(self.converted_video_path):
                    if convert_video_to_target_format(self.converted_video_path, path, ext):
                        self.update_status(f"✓ Saved video to {os.path.basename(path)}")
                        return
                    # fallback to saving by rewriting target format

                scale = self.scale_var.get()
                color = self.color_var.get()
                charset_key = self.charset_var.get()
                palette = self.palette_var.get()
                preserve_audio = self.preserve_audio_var.get()
                charset = select_charset(charset_key)
                scale = clamp_scale_for_charset(scale, charset)
                output_temp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}").name

                video_to_ascii_video(
                    self.current_path,
                    output_temp,
                    scale=scale,
                    color=color,
                    charset=charset,
                    palette=palette,
                    status_callback=self.update_status,
                )

                if preserve_audio and shutil.which("ffmpeg"):
                    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".aac").name
                    if extract_audio(self.current_path, temp_audio):
                        if ext == "avi":
                            converted = convert_video_to_target_format(output_temp, path, ext)
                        else:
                            converted = remux_audio_to_video(output_temp, temp_audio, path)
                        if os.path.exists(output_temp):
                            os.remove(output_temp)
                        if os.path.exists(temp_audio):
                            os.remove(temp_audio)
                        if converted:
                            self.update_status(f"✓ Saved video to {os.path.basename(path)}")
                            return
                    else:
                        shutil.move(output_temp, path)
                        self.update_status(f"✓ Saved video to {os.path.basename(path)}")
                        return
                else:
                    shutil.move(output_temp, path)
                    self.update_status(f"✓ Saved video to {os.path.basename(path)}")
                    return

                raise RuntimeError("Failed to save video in the requested format.")
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to save video:\n{exc}")
                self.update_status("Error saving video.")
            finally:
                self.set_controls_enabled(True)
        else:
            messagebox.showwarning("Nothing to save", "Convert an image or video first.")

    def save_converted_video(self):
        if not self.converted_video_path or not os.path.exists(self.converted_video_path):
            messagebox.showwarning("No converted video", "Convert a video first before saving the converted file.")
            return

        fmt = self.video_format_var.get()
        ext = fmt
        path = filedialog.asksaveasfilename(defaultextension=f".{ext}", filetypes=[(f"{ext.upper()} video", f"*.{ext}")])
        if not path:
            return

        if convert_video_to_target_format(self.converted_video_path, path, ext):
            self.update_status(f"✓ Saved converted video to {os.path.basename(path)}")
        else:
            messagebox.showerror("Error", "Could not save the converted video in the selected format.")
            self.update_status("Error saving converted video.")


if __name__ == "__main__":
    root = tk.Tk()
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.zib.asciitranslator")
        except Exception:
            pass
    try:
        app_dir = os.path.dirname(__file__)
        tab_icon_path = os.path.join(app_dir, "Tabimage.ico")
        if os.path.exists(tab_icon_path):
            try:
                root.iconbitmap(tab_icon_path)
            except Exception:
                pass
            try:
                icon_image = ImageTk.PhotoImage(Image.open(tab_icon_path))
                root.iconphoto(True, icon_image)
                root._icon_image = icon_image
            except Exception:
                pass
        root.update_idletasks()
    except Exception:
        pass
    app = AsciiTranslatorApp(root)
    root.mainloop()
