
from pydub import AudioSegment
import speech_recognition as sr
from io import BytesIO
import os
from flask import Flask, render_template, request, jsonify, send_from_directory, session
from flask_session import Session  # Import the Session extension
from gtts import gTTS
import logging

app = Flask(__name__)
app.secret_key = 'SDKFJSDFOWEIOF'

# Configuring the app to use Flask-Session
app.config['SESSION_TYPE'] = 'filesystem'  # used 'filesystem' session type for file storage
Session(app)

# Define the directory for audio files
audio_directory = os.path.join(app.root_path, 'static', 'audio')
if not os.path.exists(audio_directory):
    os.makedirs(audio_directory)

speech_audio_directory = os.path.join(app.root_path, 'static', 'speech_audio')
if not os.path.exists(speech_audio_directory):
    os.makedirs(speech_audio_directory)

audio_messages = []
speech_messages = []

@app.route('/')
def index():
    text = session.get('text', '')
    return render_template('index.html', audio_messages=audio_messages, speech_messages=speech_messages, text=text)

@app.route('/text-to-speech', methods=['POST'])
def text_to_speech():
    try:
        message = request.form.get('message-input')
        print('msg', message)
        if message:
            # Create a unique filename for each audio message
            output_filename = f'output_{len(audio_messages) + 1}.ogg'
            output_audio_path = os.path.join(audio_directory, output_filename)

            # Convert the message to speech using gTTS
            tts = gTTS(message, lang='en')
            tts.save(output_audio_path)

            # Add the new audio message to the audio_messages list
            audio_messages.append(output_filename)

            # Limit the list to store only the last 5 audio messages
            if len(audio_messages) > 5:
                old_audio_filename = audio_messages.pop(0)
                old_audio_path = os.path.join(audio_directory, old_audio_filename)
                os.remove(old_audio_path)  # Remove the oldest message

            return jsonify({'recognized_text': message, 'user_audio': output_filename})
        else:
            return jsonify({'error': 'No text to speak'})

    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/get-audio/<filename>')
def get_audio(filename):
    return send_from_directory(audio_directory, filename)

@app.route('/get-audio-messages', methods=['GET'])
def get_audio_messages():
    return jsonify({'audio_messages': audio_messages})

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    audio_data = request.files['audio']
    
    if audio_data:
        try:
            # Convert the uploaded audio data to an AudioSegment
            audio = AudioSegment.from_file(BytesIO(audio_data.read()))
            
            # Convert to WAV format
            audio = audio.set_channels(1)  # Set to mono if needed
            audio = audio.set_frame_rate(16000)  # Set the desired sample rate
            audio = audio.set_sample_width(2)  # Set the desired sample width
            
            # Save the converted audio to disk
            audio.export(f'{speech_audio_directory}/converted_audio.wav', format='wav')

            # Perform speech recognition on the audio using Recognizer
            r = sr.Recognizer()
            with sr.AudioFile(f'{speech_audio_directory}/converted_audio.wav') as source:
                audio_data = r.record(source)
                text = r.recognize_google(audio_data)
            
            # Store the recognized text in session storage
            session['text'] = text
            
            # Store the recognized speech in speech messages
            speech_messages.append(text)
            print(speech_messages)
            
            return jsonify({'text': text})
        except sr.UnknownValueError:
            text = "your audio is not clear. Can you repeat the message"
            return jsonify({'text': text})
        except sr.RequestError as e:
            text = f"Could not request results from Google Web Speech API; {e}"
            return jsonify({'text': text})
    else:
        return jsonify({'text': 'No audio data received'})

@app.route('/check_session')
def check_session():
    session['test_key'] = 'test_value'
    app.logger.info(f'Session data: {session.get("test_key")}')
    return f'Session data: {session.get("test_key")}'

if __name__ == '__main__':
    app.run(debug=True)
