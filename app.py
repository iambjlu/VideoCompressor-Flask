#########
'''
使用前記得先安裝 ffmpeg
sudo apt update
sudo apt install ffmpeg
'''
#########

from flask import Flask, request, send_from_directory, redirect, url_for, render_template_string
import os
import subprocess
import threading
import time
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'compressed'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 限制 50MB

ALLOWED_EXTENSIONS = {'mp4', 'mov', 'mkv', 'avi'}

# 建立資料夾
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# 上傳頁面
INDEX_HTML = '''
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0,minimum-scale=1, maximum-scale=1">
<title>影片壓縮器</title>
<link rel="stylesheet" href="https://code.getmdl.io/1.3.0/material.indigo-pink.min.css">
<script defer src="https://code.getmdl.io/1.3.0/material.min.js"></script>
<style>
    body {
            font-family: '-apple-system', 'BlinkMacSystemFont', 'SF Pro', 'SF Pro Display', 'PingFang TC', 'Inter', 'Roboto', 'AppleGothic', 'Microsoft JhengHei UI', sans-serif;
            padding: 20px;
            background-color: #d9d9d9;
        }
</style>
</head>
<body>
    <h2>影片壓縮器</h2>
    <p>支援 MP4/MOV/MKV/AVI，原始檔案大小上限 50MB。<br>壓縮後最高可達1080p，非常適合用於Discord等場景<br><br>為確保資料安全，<br>壓縮後隨即刪除原始影片、兩分鐘後刪除壓縮後的影片。</p>
    <form method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept="video/*" class="mdl-button mdl-js-button mdl-button--raised" required><br><br>
        <input type="submit" class="mdl-button mdl-js-button mdl-button--raised mdl-button--colored" value="上傳並壓縮">
    </form>
</body>
</html>
'''

# 結果頁面（顯示下載連結）
RESULT_HTML = '''
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0,minimum-scale=1, maximum-scale=1">
<title>壓縮完成</title>
<link rel="stylesheet" href="https://code.getmdl.io/1.3.0/material.indigo-pink.min.css">
<script defer src="https://code.getmdl.io/1.3.0/material.min.js"></script>
<style>
    body {
            font-family: '-apple-system', 'BlinkMacSystemFont', 'SF Pro', 'SF Pro Display', 'PingFang TC', 'Inter', 'Roboto', 'AppleGothic', 'Microsoft JhengHei UI', sans-serif;
        }
</style>
</head>
<body>
    <h3>✅ 壓縮成功！</h3>
    <p>請在 2 分鐘內下載，檔案將自動刪除：</p>
    <a href="{{ url }}" target="_blank">{{ url }}</a>
</body>
</html>
'''

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def compress_video(input_path, output_path):
    command = [
        'ffmpeg',
        '-i', input_path,
        '-r', '30',
        '-vf', 'scale=w=1920:h=1080:force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2',
        '-c:v', 'libx264',
        '-b:v', '1.5M',
        '-preset', 'fast',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-movflags', '+faststart',
        output_path
    ]
    subprocess.run(command, check=True)

def schedule_deletion(filepath, delay=120):
    def delete_file():
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"[已自動刪除] {filepath}")
        except Exception as e:
            print(f"[刪除失敗] {e}")
    threading.Timer(delay, delete_file).start()

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files.get('file')
        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            timestamp = str(int(time.time()))
            filename = f"{timestamp}.{ext}"
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            output_filename = f"compressed_{timestamp}.{ext}"
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
            file.save(input_path)

            try:
                compress_video(input_path, output_path)
                os.remove(input_path)
                schedule_deletion(output_path, delay=120)
                #redirect 到結果頁面，防止刷新重複壓縮
                return redirect(url_for('result_page', filename=output_filename))
            except Exception as e:
                return f"❌ 壓縮失敗：{e}"
        else:
            return "❌ 請上傳正確格式的影片（mp4/mov/mkv/avi）且小於 50MB。"
    return render_template_string(INDEX_HTML)

@app.route('/result/<filename>')
def result_page(filename):
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if not os.path.exists(output_path):
        return redirect(url_for('upload_file'))
    url = url_for('download_file', filename=filename, _external=True)
    return render_template_string(RESULT_HTML, url=url)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7000, debug=True)
