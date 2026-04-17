import gradio as gr
import yt_dlp
import json
import os
from datetime import datetime

HISTORY_FILE = "history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(data):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def add_to_history(vid, title, author, thumb, duration=''):
    hist = load_history()
    hist = [h for h in hist if h['id'] != vid]
    hist.insert(0, {
        'id': vid,
        'title': title or 'Untitled',
        'author': author or 'Unknown',
        'thumb': thumb or f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
        'duration': duration or '',
        'played_at': datetime.now().isoformat()
    })
    save_history(hist[:50])

def get_stream_url(video_url, mode='audio'):
    """Extract direct stream URL from YouTube (No Ads)"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    if mode == 'audio':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],        })
    else:
        ydl_opts.update({
            'format': 'bestvideo+bestaudio/best',
        })
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            if mode == 'audio':
                # Get audio URL
                audio_url = info.get('url') or info.get('webpage_url')
                return audio_url, info.get('title', ''), info.get('uploader', ''), info.get('thumbnail', '')
            else:
                return video_url, info.get('title', ''), info.get('uploader', ''), info.get('thumbnail', '')
    except Exception as e:
        return None, str(e), '', ''

def search_youtube(query, max_results=12):
    """Search YouTube without downloading"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'default_search': 'ytsearch',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            results = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            videos = []
            for entry in results.get('entries', []):
                if entry:
                    videos.append({
                        'id': entry.get('id', ''),
                        'title': entry.get('title', 'Untitled'),
                        'author': entry.get('uploader', 'Unknown'),
                        'thumb': f"https://i.ytimg.com/vi/{entry.get('id', '')}/mqdefault.jpg",
                        'duration': entry.get('duration', 0),
                        'url': f"https://www.youtube.com/watch?v={entry.get('id', '')}"
                    })
            return videos
    except Exception as e:
        print(f"Search error: {e}")
        return []

def format_duration(seconds):
    if not seconds:
        return ''
    h = seconds // 3600    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f'{h}:{m:02d}:{s:02d}'
    return f'{m}:{s:02d}'

def create_app():
    with gr.Blocks(title="TubePlay Premium", theme=gr.themes.Soft(primary_hue="blue")) as app:
        gr.Markdown("""
        # 🎵 TubePlay Premium
        ### Ad-Free YouTube Player with Background Play
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                search_input = gr.Textbox(
                    label="Search YouTube",
                    placeholder="Type to search...",
                    lines=1
                )
                search_btn = gr.Button("🔍 Search", variant="primary")
                
                mode_radio = gr.Radio(
                    choices=["🎵 Audio Only", "📺 Video Mode"],
                    value="🎵 Audio Only",
                    label="Playback Mode"
                )
                
                status_text = gr.Textbox(label="Status", interactive=False)
                
            with gr.Column(scale=2):
                results_gallery = gr.Gallery(
                    label="Search Results",
                    show_label=False,
                    columns=3,
                    rows=2,
                    object_fit="cover",
                    height=400
                )
        
        # History Section
        gr.Markdown("### 🕒 Recently Played")
        history_gallery = gr.Gallery(
            label="History",
            show_label=False,
            columns=3,
            rows=2,
            object_fit="cover",
            height=300
        )        
        # Hidden components for data
        selected_video_id = gr.State('')
        selected_video_url = gr.State('')
        current_mode = gr.State('audio')
        
        # Player
        gr.Markdown("### 🎮 Player")
        with gr.Row():
            with gr.Column():
                audio_player = gr.Audio(label="Audio Player", visible=True)
                video_player = gr.Video(label="Video Player", visible=False)
        
        def on_search(query):
            if not query:
                return [], "Please enter a search term"
            
            videos = search_youtube(query)
            if videos:
                # Create gallery items with thumbnails
                gallery_items = [(v['thumb'], f"{v['title'][:50]}\n{v['author']}") for v in videos]
                return gallery_items, f"Found {len(videos)} videos"
            return [], "No results found"
        
        def on_video_select(evt: gr.SelectData, videos):
            if not videos or evt.index >= len(videos):
                return None, None, "No video selected", gr.update(visible=True), gr.update(visible=False)
            
            video = videos[evt.index]
            vid_id = video['id']
            vid_url = video['url']
            mode = current_mode.value
            
            # Add to history
            add_to_history(
                vid_id,
                video['title'],
                video['author'],
                video['thumb'],
                format_duration(video.get('duration', 0))
            )
            
            # Get stream URL
            stream_url, title, author, thumb = get_stream_url(vid_url, 'audio' if 'Audio' in mode else 'video')
            
            if not stream_url:
                return None, None, f"Error: {title}", gr.update(visible=True), gr.update(visible=False)
            
            # Update history display
            hist = load_history()            hist_items = [(v['thumb'], f"{v['title'][:40]}\n{v['author']}") for v in hist[:6]]
            
            if 'Audio' in mode:
                return (stream_url, vid_url, f"🎵 Playing: {title[:50]}", 
                        gr.update(value=stream_url, visible=True), gr.update(visible=False))
            else:
                return (stream_url, vid_url, f"📺 Playing: {title[:50]}", 
                        gr.update(visible=False), gr.update(value=stream_url, visible=True))
        
        def on_mode_change(mode):
            current_mode.value = 'audio' if 'Audio' in mode else 'video'
            return (gr.update(visible='Audio' in mode), 
                    gr.update(visible='Video' in mode),
                    f"Mode changed to: {mode}")
        
        # Event handlers
        search_btn.click(
            fn=on_search,
            inputs=[search_input],
            outputs=[results_gallery, status_text]
        )
        
        search_input.submit(
            fn=on_search,
            inputs=[search_input],
            outputs=[results_gallery, status_text]
        )
        
        results_gallery.select(
            fn=on_video_select,
            inputs=[results_gallery],
            outputs=[audio_player, video_player, status_text, audio_player, video_player]
        )
        
        mode_radio.change(
            fn=on_mode_change,
            inputs=[mode_radio],
            outputs=[audio_player, video_player, status_text]
        )
        
        # Load history on startup
        app.load(
            fn=lambda: [(v['thumb'], f"{v['title'][:40]}\n{v['author']}") for v in load_history()[:6]],
            inputs=[],
            outputs=[history_gallery]
        )
    
    return app

if __name__ == "__main__":    app = create_app()
    app.launch(server_name="0.0.0.0", server_port=7860)
