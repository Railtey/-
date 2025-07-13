import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from io import BytesIO
import requests
import yt_dlp
import json
import re
import sys

search_results = []  # 누적된 검색 결과 (dict 리스트)
result_frames = []   # 각 결과 프레임 참조 리스트

base_path = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__)
ffmpeg_path = os.path.join(base_path, "ffmpeg", "bin", "ffmpeg.exe")

def is_url(text):
    return text.startswith("http://") or text.startswith("https://")

def remove_result(idx):
    frame = result_frames[idx]
    frame.destroy()

    del result_frames[idx]
    del search_results[idx]

    # 삭제 후 나머지 인덱스 재조정 (삭제 버튼 command 갱신)
    for i in range(idx, len(result_frames)):
        btn = result_frames[i].children.get('del_btn')
        if btn:
            btn.config(command=lambda i=i: remove_result(i))

def add_result_to_gui_with_thumbnail(entry, thumbnail_url=None):
    global search_results, result_frames

    video_url = entry.get('url')

    # 중복 체크
    if any(item['url'] == video_url for item in search_results):
        return  # 중복 방지

    kind = entry.get('type', 'Youtube')
    if kind == "YoutubePlaylist":
        label_type = "[재생목록]"
    elif kind == "Youtube":
        label_type = "[영상]"
    else:
        label_type = "[기타]"

    title = f"{label_type} {entry.get('title')}"
    idx = len(search_results)

    frame = ttk.Frame(results_frame, padding=5)
    frame.grid(row=idx, column=0, sticky="w")

    #thumb_photo = None
    if thumbnail_url:
        try:
            thumb_data = requests.get(thumbnail_url, timeout=10).content
            thumb_image = Image.open(BytesIO(thumb_data))
            thumb_image = thumb_image.resize((120, 90))
            thumb_photo = ImageTk.PhotoImage(thumb_image)
        except Exception:
            thumb_photo = None

    if thumb_photo:
        label_img = ttk.Label(frame, image=thumb_photo)
        label_img.image = thumb_photo
        label_img.grid(row=0, column=0)

    label_title = ttk.Label(frame, text=title, wraplength=400)
    label_title.grid(row=0, column=1, sticky="w")

    del_btn = ttk.Button(frame, text="삭제", width=6)
    del_btn.grid(row=0, column=2, padx=5)
    del_btn._name = 'del_btn'
    del_btn.config(command=lambda i=idx: remove_result(i))

    result_frames.append(frame)
    search_results.append({
        'url': video_url,
        'title': entry.get('title'),
        'type': kind
    })

def fetch_thumbnail_and_add(entry):
    """
    저장된 entry에서 URL, 제목, 타입 정보로
    yt_dlp로 다시 영상 정보 받아서 썸네일 포함해서 GUI에 추가
    """
    video_url = entry.get('url')

    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'extract_flat': 'in_playlist',
        'ffmpeg_location': ffmpeg_path,
    }

    thumbnail_url = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            thumbnail_url = info.get('thumbnail', None)
    except Exception:
        thumbnail_url = None

    add_result_to_gui_with_thumbnail(entry, thumbnail_url)

def search_youtube(query, results_frame):
    global search_results, result_frames

    is_playlist_url = is_url(query) and 'playlist' in query

    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'ffmpeg_location': ffmpeg_path,
    }

    if not is_playlist_url:
        ydl_opts['extract_flat'] = 'in_playlist'

    duplicate_count = 0

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if is_url(query):
                info = ydl.extract_info(query, download=False)
                if 'entries' in info:
                    entries = info['entries']
                else:
                    entries = [info]
            else:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                entries = info.get('entries', [])
    except Exception as e:
        messagebox.showerror("검색 오류", f"검색 중 오류가 발생했습니다:\n{e}")
        return

    start_idx = len(search_results)

    for idx, entry in enumerate(entries):
        kind = entry.get('ie_key', 'Youtube')
        if kind == "YoutubePlaylist":
            video_url = f"https://www.youtube.com/playlist?list={entry.get('id')}"
        elif kind == "Youtube":
            video_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
        else:
            continue

        if any(item['url'] == video_url for item in search_results):
            duplicate_count += 1
            continue

        label_type = "[재생목록]" if kind == "YoutubePlaylist" else "[영상]"
        title = f"{label_type} {entry.get('title')}"
        thumbnail_url = entry.get('thumbnail')

        try:
            thumb_data = requests.get(thumbnail_url, timeout=10).content
            thumb_image = Image.open(BytesIO(thumb_data))
            thumb_image = thumb_image.resize((120, 90))
            thumb_photo = ImageTk.PhotoImage(thumb_image)
        except Exception:
            thumb_photo = None

        frame = ttk.Frame(results_frame, padding=5)
        frame.grid(row=start_idx + idx, column=0, sticky="w")

        if thumb_photo:
            label_img = ttk.Label(frame, image=thumb_photo)
            label_img.image = thumb_photo
            label_img.grid(row=0, column=0)

        label_title = ttk.Label(frame, text=title, wraplength=400)
        label_title.grid(row=0, column=1, sticky="w")

        del_btn = ttk.Button(frame, text="삭제", width=6)
        del_btn.grid(row=0, column=2, padx=5)
        del_btn._name = 'del_btn'
        del_btn.config(command=lambda i=start_idx + idx: remove_result(i))

        result_frames.append(frame)
        search_results.append({
            'url': video_url,
            'title': entry.get('title'),
            'type': kind
        })

    if duplicate_count > 0:
        messagebox.showwarning("중복 영상", f"{duplicate_count}개의 중복된 영상은 추가되지 않았습니다.")

def download_all_mp3(download_dir, progress_callback):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
        'quiet': False,
        'ffmpeg_location': ffmpeg_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for entry in search_results:
            progress_callback(f"다운로드 중: {entry['title']}")
            ydl.download([entry['url']])

def start_download_mp3():
    if not search_results:
        messagebox.showerror("오류", "먼저 검색하세요.")
        return

    download_dir = filedialog.askdirectory(title="저장할 폴더 선택")
    if not download_dir:
        return

    total_files = len(search_results)
    stop_download = threading.Event()

    # 다운로드 진행창
    progress_window = tk.Toplevel(root)
    progress_window.title("다운로드 진행")
    progress_window.geometry("450x230")

    lbl_current = ttk.Label(progress_window, text="현재 파일 진행")
    lbl_current.pack(pady=3)
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(progress_window, maximum=100, length=400, variable=progress_var)
    progress_bar.pack(padx=10, pady=3)

    lbl_total = ttk.Label(progress_window, text="전체 진행")
    lbl_total.pack(pady=3)
    total_var = tk.DoubleVar()
    total_bar = ttk.Progressbar(progress_window, maximum=100, length=400, variable=total_var)
    total_bar.pack(padx=10, pady=3)

    cancel_btn = ttk.Button(progress_window, text="취소", width=10, command=stop_download.set)
    cancel_btn.pack(pady=10)

    def run_download():
        start_button.config(state=tk.DISABLED)
        try:
            for idx, entry in enumerate(search_results):
                if stop_download.is_set():
                    status_var.set("다운로드 취소됨.")
                    break

                status_var.set(f"{entry['title']} 다운로드 중 ({idx + 1}/{total_files})")

                def progress_hook(d):
                    if stop_download.is_set():
                        raise Exception("다운로드 취소됨")

                    if d['status'] == 'downloading':
                        total = d.get('total_bytes') or d.get('total_bytes_estimate')
                        downloaded = d.get('downloaded_bytes', 0)
                        if total:
                            percent = downloaded / total * 100
                            progress_var.set(percent)
                    elif d['status'] == 'finished':
                        progress_var.set(100)

                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
                    'quiet': True,
                    'progress_hooks': [progress_hook],
                    'ffmpeg_location': ffmpeg_path,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }]
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([entry['url']])

                # 다음 파일 준비
                progress_var.set(0)
                total_progress = (idx + 1) / total_files * 100
                total_var.set(total_progress)

            if stop_download.is_set():
                messagebox.showinfo("취소됨", "다운로드가 취소되었습니다.")
            else:
                status_var.set("다운로드 완료!")
                messagebox.showinfo("완료", "모든 MP3 다운로드가 끝났습니다.")
        except Exception as e:
            if str(e) == "다운로드 취소됨":
                messagebox.showinfo("취소됨", "다운로드가 취소되었습니다.")
                status_var.set("다운로드 취소됨.")
            else:
                messagebox.showerror("오류", f"오류 발생: {e}")
                status_var.set("오류 발생.")
        finally:
            progress_window.destroy()
            start_button.config(state=tk.NORMAL)

    threading.Thread(target=run_download).start()

def start_download_mp4():
    if not search_results:
        messagebox.showerror("오류", "다운로드할 항목이 없습니다.")
        return

    download_dir = filedialog.askdirectory(title="저장할 폴더 선택")
    if not download_dir:
        return

    total_files = len(search_results)
    stop_download = threading.Event()

    progress_window = tk.Toplevel(root)
    progress_window.title("MP4 다운로드 진행")
    progress_window.geometry("450x230")

    ttk.Label(progress_window, text="현재 파일 진행").pack(pady=3)
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(progress_window, maximum=100, length=400, variable=progress_var)
    progress_bar.pack(padx=10, pady=3)

    ttk.Label(progress_window, text="전체 진행").pack(pady=3)
    total_var = tk.DoubleVar()
    total_bar = ttk.Progressbar(progress_window, maximum=100, length=400, variable=total_var)
    total_bar.pack(padx=10, pady=3)

    cancel_btn = ttk.Button(progress_window, text="취소", width=10, command=stop_download.set)
    cancel_btn.pack(pady=10)

    def run_download():
        start_button.config(state=tk.DISABLED)
        mp4_button.config(state=tk.DISABLED)
        thumb_button.config(state=tk.DISABLED)
        try:
            for idx, entry in enumerate(search_results):
                if stop_download.is_set():
                    status_var.set("다운로드 취소됨.")
                    break

                status_var.set(f"{entry['title']} MP4 다운로드 중 ({idx+1}/{total_files})")

                def progress_hook(d):
                    if stop_download.is_set():
                        raise Exception("다운로드 취소됨")
                    if d['status'] == 'downloading':
                        total = d.get('total_bytes') or d.get('total_bytes_estimate')
                        downloaded = d.get('downloaded_bytes', 0)
                        if total:
                            progress_var.set(downloaded / total * 100)
                    elif d['status'] == 'finished':
                        progress_var.set(100)

                ydl_opts = {
                    'format': 'bestvideo+bestaudio/best',
                    'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
                    'quiet': True,
                    'progress_hooks': [progress_hook],
                    'merge_output_format': 'mp4',
                    'ffmpeg_location': ffmpeg_path,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([entry['url']])

                progress_var.set(0)
                total_var.set((idx + 1) / total_files * 100)

            if stop_download.is_set():
                messagebox.showinfo("취소됨", "다운로드가 취소되었습니다.")
            else:
                status_var.set("MP4 다운로드 완료!")
                messagebox.showinfo("완료", "모든 MP4 다운로드가 완료되었습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"오류 발생: {e}")
        finally:
            progress_window.destroy()
            start_button.config(state=tk.NORMAL)
            mp4_button.config(state=tk.NORMAL)
            thumb_button.config(state=tk.NORMAL)

    threading.Thread(target=run_download).start()

def start_download_thumbnails():
    if not search_results:
        messagebox.showerror("오류", "다운로드할 항목이 없습니다.")
        return

    download_dir = filedialog.askdirectory(title="썸네일 저장할 폴더 선택")
    if not download_dir:
        return

    total_files = len(search_results)
    stop_download = threading.Event()

    progress_window = tk.Toplevel(root)
    progress_window.title("썸네일 다운로드 진행")
    progress_window.geometry("450x230")  # 높이 늘림

    ttk.Label(progress_window, text="현재 파일 진행").pack(pady=3)
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(progress_window, maximum=100, length=400, variable=progress_var)
    progress_bar.pack(padx=10, pady=3)

    ttk.Label(progress_window, text="전체 진행").pack(pady=3)
    total_var = tk.DoubleVar()
    total_bar = ttk.Progressbar(progress_window, maximum=100, length=400, variable=total_var)
    total_bar.pack(padx=10, pady=3)

    cancel_btn = ttk.Button(progress_window, text="취소", width=10, command=stop_download.set)
    cancel_btn.pack(pady=10)

    def sanitize_filename(filename):
        return re.sub(r'[\\/*?:"<>|]', "", filename)

    def run_download():
        start_button.config(state=tk.DISABLED)
        mp4_button.config(state=tk.DISABLED)
        thumb_button.config(state=tk.DISABLED)

        try:
            for idx, entry in enumerate(search_results):
                if stop_download.is_set():
                    status_var.set("썸네일 다운로드 취소됨.")
                    break

                status_var.set(f"{entry['title']} 썸네일 다운로드 중 ({idx+1}/{total_files})")

                ydl_opts = {'quiet': True, 'skip_download': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(entry['url'], download=False)

                thumb_url = info.get('thumbnail')
                if thumb_url:
                    try:
                        resp = requests.get(thumb_url, timeout=15)
                        resp.raise_for_status()
                        ext = os.path.splitext(thumb_url)[1].split('?')[0]
                        if ext.lower() not in ['.jpg', '.jpeg', '.png']:
                            ext = '.jpg'
                        safe_title = sanitize_filename(entry['title'])
                        filename = f"{safe_title}_thumbnail{ext}"
                        filepath = os.path.join(download_dir, filename)

                        with open(filepath, 'wb') as f:
                            f.write(resp.content)

                    except Exception as e:
                        print(f"썸네일 다운로드 실패: {entry['title']} - {e}")

                progress_var.set(100)  # 현재 파일 완료
                total_var.set((idx + 1) / total_files * 100)  # 전체 진행률 갱신

            if stop_download.is_set():
                messagebox.showinfo("취소됨", "썸네일 다운로드가 취소되었습니다.")
            else:
                status_var.set("썸네일 다운로드 완료!")
                messagebox.showinfo("완료", "모든 썸네일 다운로드가 완료되었습니다.")

        except Exception as e:
            messagebox.showerror("오류", f"오류 발생: {e}")

        finally:
            progress_window.destroy()
            start_button.config(state=tk.NORMAL)
            mp4_button.config(state=tk.NORMAL)
            thumb_button.config(state=tk.NORMAL)

    threading.Thread(target=run_download).start()

def save_search_list():
    if not search_results:
        messagebox.showerror("오류", "저장할 검색목록이 없습니다.")
        return
    file_path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON 파일", "*.json")],
        title="검색목록 저장"
    )
    if not file_path:
        return

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(search_results, f, ensure_ascii=False, indent=2)

    messagebox.showinfo("저장 완료", f"검색목록이 저장되었습니다:\n{file_path}")

def load_search_list():
    file_path = filedialog.askopenfilename(
        defaultextension=".json",
        filetypes=[("JSON 파일", "*.json")],
        title="검색목록 불러오기"
    )
    if not file_path:
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            loaded_list = json.load(f)
    except Exception as e:
        messagebox.showerror("오류", f"파일을 읽는 중 오류가 발생했습니다:\n{e}")
        return

    status_var.set("검색목록 불러오는 중...")

    def load_and_add_all():
        for entry in loaded_list:
            fetch_thumbnail_and_add(entry)
        status_var.set(f"{len(loaded_list)}개 검색목록 불러오기 완료")

    threading.Thread(target=load_and_add_all).start()

def on_search():
    query = search_entry.get().strip()
    if not query:
        messagebox.showerror("오류", "검색어를 입력하세요.")
        return

    status_var.set("검색 중...")
    def run_search():
        search_youtube(query, results_frame)
        status_var.set("검색 완료.")

    threading.Thread(target=run_search).start()
    search_entry.delete(0, tk.END)

def show_debug_info():
    if not search_results:
        messagebox.showinfo("디버깅", "검색 결과가 비어 있습니다.")
        return

    debug_window = tk.Toplevel(root)
    debug_window.title("디버그 정보")
    debug_window.geometry("600x400")

    text_widget = tk.Text(debug_window, wrap="none")
    text_widget.pack(fill=tk.BOTH, expand=True)

    scrollbar_y = ttk.Scrollbar(debug_window, orient="vertical", command=text_widget.yview)
    scrollbar_y.pack(side="right", fill="y")
    text_widget.configure(yscrollcommand=scrollbar_y.set)

    scrollbar_x = ttk.Scrollbar(debug_window, orient="horizontal", command=text_widget.xview)
    scrollbar_x.pack(side="bottom", fill="x")
    text_widget.configure(xscrollcommand=scrollbar_x.set)

    import json
    pretty_json = json.dumps(search_results, ensure_ascii=False, indent=2)
    text_widget.insert("1.0", pretty_json)

    text_widget.config(state="disabled")

def clear_all_results():
    global search_results, result_frames

    for frame in result_frames:
        frame.destroy()

    search_results.clear()
    result_frames.clear()
    status_var.set("모든 검색 결과가 삭제되었습니다.")

# Tkinter GUI 초기화
root = tk.Tk()
root.title("유튜브 만능 다운로더")
root.geometry("700x550")
root.configure(bg="white")

# 검색창
search_frame = ttk.Frame(root, padding=10)
search_frame.pack(fill=tk.X)

search_entry = ttk.Entry(search_frame, width=50,)
search_entry.pack(side=tk.LEFT, padx=5)

search_button = ttk.Button(search_frame, text="검색", command=on_search)
search_button.pack(side=tk.LEFT)

# 버튼 모음 (다운로드, 저장, 불러오기)
button_frame = ttk.Frame(root)
button_frame.pack(fill=tk.X, padx=10, pady=5)

start_button = ttk.Button(button_frame, text="일괄 mp3 다운로드", command=start_download_mp3)
start_button.pack(side=tk.LEFT, padx=5)

mp4_button = ttk.Button(button_frame, text="일괄 mp4 다운", command=start_download_mp4)
mp4_button.pack(side=tk.LEFT, padx=5)

thumb_button = ttk.Button(button_frame, text="일괄 썸네일 다운로드", command=start_download_thumbnails)
thumb_button.pack(side=tk.LEFT, padx=5)

save_button = ttk.Button(button_frame, text="검색목록 저장", command=save_search_list)
save_button.pack(side=tk.LEFT, padx=5)

load_button = ttk.Button(button_frame, text="검색목록 불러오기", command=load_search_list)
load_button.pack(side=tk.LEFT, padx=5)

clear_button = ttk.Button(button_frame, text="목록 비우기", command=lambda: clear_all_results())
clear_button.pack(side=tk.LEFT, padx=5)

# 결과 표시 영역 (스크롤 가능)
results_frame = ttk.Frame(root)
results_frame.pack(fill=tk.BOTH, expand=True)

canvas = tk.Canvas(results_frame, bg="white")
scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=canvas.yview)
scrollable_frame = ttk.Frame(canvas)

def _on_mousewheel(event):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

scrollable_frame.bind_all("<MouseWheel>", _on_mousewheel)

scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)

canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

results_frame = scrollable_frame

# 상태 표시줄
status_var = tk.StringVar(value="준비됨")
status_label = ttk.Label(root, textvariable=status_var, relief=tk.SUNKEN, anchor="w")
status_label.pack(fill=tk.X)

root.mainloop()

