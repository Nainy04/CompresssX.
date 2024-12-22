from flask import Flask, render_template, request, send_file, redirect, url_for, session
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configure upload and compressed directories
UPLOAD_FOLDER = 'uploads'
COMPRESSED_FOLDER = 'compressed'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['COMPRESSED_FOLDER'] = COMPRESSED_FOLDER

# Ensure upload and compressed folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(COMPRESSED_FOLDER, exist_ok=True)

# Huffman Node Class for TXT Compression
class HuffmanNode:
    def __init__(self, char, freq):
        self.char = char
        self.freq = freq
        self.left = None
        self.right = None

# Huffman Encoding Functions
def build_huffman_tree(data):
    frequency = {char: data.count(char) for char in set(data)}
    nodes = [HuffmanNode(char, freq) for char, freq in frequency.items()]

    while len(nodes) > 1:
        nodes.sort(key=lambda x: x.freq)
        left, right = nodes.pop(0), nodes.pop(0)
        new_node = HuffmanNode(None, left.freq + right.freq)
        new_node.left = left
        new_node.right = right
        nodes.append(new_node)

    return nodes[0]

def generate_huffman_codes(root, current_code='', codes=None):
    if codes is None:
        codes = {}
    if root is None:
        return codes
    if root.char is not None:
        codes[root.char] = current_code
    generate_huffman_codes(root.left, current_code + '0', codes)
    generate_huffman_codes(root.right, current_code + '1', codes)
    return codes

def huffman_compress(data):
    root = build_huffman_tree(data)
    huffman_codes = generate_huffman_codes(root)
    compressed_data = ''.join(huffman_codes[char] for char in data)
    return compressed_data, huffman_codes

# Run-Length Encoding (RLE) for JPEG and PNG
def rle_compress(data):
    compressed = []
    count = 1
    for i in range(1, len(data)):
        if data[i] == data[i - 1]:
            count += 1
        else:
            compressed.append((data[i - 1], count))
            count = 1
    compressed.append((data[-1], count))
    return compressed

# Binary Transformation for DOC Files
def binary_transform(data):
    return ''.join(format(ord(char), '08b') for char in data)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return 'No file part', 400

    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    compressed_file_path = os.path.join(app.config['COMPRESSED_FOLDER'], f"compressed_{filename}.cmp")

    try:
        with open(filepath, 'rb') as f:
            data = f.read()

        if filename.endswith('.txt'):
            compressed_data, _ = huffman_compress(data.decode('utf-8'))
            compression_ratio = 100 - (len(compressed_data) / (len(data) * 8)) * 100
        elif filename.endswith(('.jpeg', '.png')):
            compressed_data = rle_compress(data)
            compression_ratio = 100 - (len(compressed_data) / len(data)) * 100
        elif filename.endswith('.doc'):
            compressed_data = binary_transform(data.decode('utf-8'))
            compression_ratio = 100 - (len(compressed_data) / (len(data) * 8)) * 100
        else:
            return 'Unsupported file type', 400

        with open(compressed_file_path, 'w') as f:
            f.write(str(compressed_data))

        session['compression_ratio'] = round(compression_ratio, 2)
        session['original_size'] = len(data)
        session['compressed_size'] = len(str(compressed_data))
        session['compressed_file_path'] = compressed_file_path

    except Exception as e:
        return f"Compression failed: {e}", 500

    return redirect(url_for('result'))

@app.route('/result')
def result():
    original_size = session.get('original_size')
    compressed_size = session.get('compressed_size')
    compression_ratio = session.get('compression_ratio')
    return render_template('result.html', original_size=original_size, compressed_size=compressed_size, compression_ratio=compression_ratio)

@app.route('/download')
def download():
    compressed_file_path = session.get('compressed_file_path')
    if not os.path.exists(compressed_file_path):
        return 'File not found', 404
    return send_file(compressed_file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)