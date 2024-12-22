import os
import re
import string
import google.generativeai as genai
import PIL.Image
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_from_directory
from flask_cors import CORS

# Configure API Key
GOOGLE_API_KEY = 'YOUR GOOGLE API KEY'
genai.configure(api_key=GOOGLE_API_KEY)

# Flask setup
app = Flask(__name__)
app.secret_key = "supersecretkey"  # For session management
CORS(app)

# Path for static files
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Helper Functions
def format_response(response, max_words=50):
    cleaned_response = re.sub(r'[^\w\s.,!?\'"-]', '', response)
    single_line_response = re.sub(r'\s+', ' ', cleaned_response).strip()

    if single_line_response and single_line_response[-1] not in string.punctuation:
        single_line_response += "."

    words = single_line_response.split()
    return ' '.join(words[:max_words])

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/start-chat', methods=['POST'])
def start_chat():
    session['pnr'] = request.form['pnr']
    session['name'] = request.form['name']
    # Initialize chat history in session
    session['chat_history'] = []
    return redirect(url_for('chat'))

@app.route('/chat')
def chat():
    if 'pnr' in session and 'name' in session:
        # Retrieve chat history from session
        chat_history = session.get('chat_history', [])
        return render_template('chat.html', pnr=session['pnr'], name=session['name'], chat_history=chat_history)
    return redirect(url_for('home'))

@app.route('/chat-api', methods=['POST'])
def chat_api():
    chat_history = session.get('chat_history', [])
    
    if 'image' in request.files:
        # Handle Image Input
        file = request.files['image']
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{file.filename}")
        file.save(img_path)

        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            with PIL.Image.open(img_path) as img:
                myfile = genai.upload_file(img_path)
                result = model.generate_content([myfile, "Please analyze this image and describe any actionable issues briefly, as if you're a professional customer care agent."])

            # Save the image and response to the chat history
            img_url = url_for('uploaded_file', filename=f"temp_{file.filename}")
            chat_history.append({"type": "image", "content": img_url, "response": format_response(result.text)})

            # Save chat history back to session
            session['chat_history'] = chat_history

            return jsonify({"response": format_response(result.text), "image": img_url, "chat_history": chat_history})

        except Exception as e:
            return jsonify({"error": str(e)})

    elif 'message' in request.form:
        # Handle Text Input
        message = request.form['message']
        pnr = session.get('pnr', 'Unknown')
        name = session.get('name', 'Guest')

        if not message:
            return jsonify({"error": "No message provided."}), 400

        prompt = f"Act as a professional customer care assistant for Indian Railways. Passenger Name: {name}, PNR: {pnr}. {message}. use the {name } , {pnr} only when required  not every time "
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            result = model.generate_content([prompt])

            # Save the text and response to the chat history
            chat_history.append({"type": "text", "content": message, "response": format_response(result.text)})

            # Save chat history back to session
            session['chat_history'] = chat_history

            return jsonify({"response": format_response(result.text), "chat_history": chat_history})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "No message or image provided."}), 400

# Serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
