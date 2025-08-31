import os
import re
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, Response
from bs4 import BeautifulSoup
import yt_dlp
from io import BytesIO
from urllib.parse import quote

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

def is_valid_instagram_url(url):
    """Check if the URL is a valid Instagram Reel URL"""
    patterns = [
        r'https?://(www\.)?instagram\.com/reel/',
        r'https?://(www\.)?instagram\.com/p/',
        r'https?://(www\.)?instagram\.com/tv/'
    ]
    return any(re.match(pattern, url) for pattern in patterns)

def extract_video_url(instagram_url):
    """Extract video URL from Instagram page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(instagram_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for video tags
        video_tags = soup.find_all('video')
        for video in video_tags:
            if video.get('src'):
                return video['src']
        
        # Alternative method: look for meta tags
        meta_tags = soup.find_all('meta', property='og:video')
        for meta in meta_tags:
            if meta.get('content'):
                return meta['content']
        
        return None
        
    except Exception as e:
        print(f"Error extracting video URL: {e}")
        return None

def get_video_stream_with_ytdlp(url):
    """Get video stream using yt-dlp"""
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info['url']
            title = info.get('title', 'instagram_reel')
            
            # Clean title for filename
            clean_title = re.sub(r'[^\w\-_\. ]', '_', title)
            filename = f"{clean_title}.mp4"
            
            return video_url, filename
    except Exception as e:
        return None, str(e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url', '').strip()
    
    if not url:
        flash('Please enter an Instagram Reel URL', 'error')
        return redirect(url_for('index'))
    
    if not is_valid_instagram_url(url):
        flash('Please enter a valid Instagram Reel URL', 'error')
        return redirect(url_for('index'))
    
    try:
        # Method 1: Try direct extraction
        video_url = extract_video_url(url)
        
        if video_url:
            # Stream the video directly to user
            response = requests.get(video_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Generate filename
            filename = "instagram_reel.mp4"
            
            return Response(
                response.iter_content(chunk_size=8192),
                content_type=response.headers['Content-Type'],
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Length': response.headers.get('Content-Length', '')
                }
            )
        
        # Method 2: Fallback to yt-dlp
        else:
            video_url, filename = get_video_stream_with_ytdlp(url)
            
            if video_url:
                response = requests.get(video_url, stream=True, timeout=30)
                response.raise_for_status()
                
                return Response(
                    response.iter_content(chunk_size=8192),
                    content_type=response.headers['Content-Type'],
                    headers={
                        'Content-Disposition': f'attachment; filename="{filename}"',
                        'Content-Length': response.headers.get('Content-Length', '')
                    }
                )
            else:
                flash(f'Failed to download video: {filename}', 'error')
                return redirect(url_for('index'))
                
    except Exception as e:
        flash(f'Error downloading video: {str(e)}', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)