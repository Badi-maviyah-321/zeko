from flask import Flask, request, jsonify, send_from_directory
import os
import logging
from threading import Thread
import speech_recognition as sr
import pyttsx3
import subprocess
import webbrowser
import datetime
import time
import requests
import wikipedia
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from AppOpener import open, close
import ctypes
import cv2
import keyboard
import pyjokes
from translate import Translator
import wolframalpha
import speedtest

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static')

# Initialize recognizer and text-to-speech engine
try:
    recognizer = sr.Recognizer()
    engine = pyttsx3.init()
    logger.info("Speech recognition and text-to-speech initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize speech modules: {e}")

# Configuration – REPLACE THESE VALUES WITH YOUR INFORMATION
EMAIL_ADDRESS = "mycoding321@gmail.com"
EMAIL_PASSWORD = "failfail00."  # Use app password if 2FA is enabled
WEATHER_API_KEY = "your_openweathermap_api_key"
NEWS_API_KEY = "your_newsapi_key"
WOLFRAM_APP_ID = "your_wolframalpha_app_id"
CITY_NAME = "surat"
MEDIA_FOLDER = "media"
BOSS_WORD = "Boss"  # Customize this with your preferred word

# Create media folder if it doesn't exist
os.makedirs(MEDIA_FOLDER, exist_ok=True)

# Translator setup
translator = Translator(to_lang="es")

summaries = []  # To store session summaries

def speak(text):
    """Converts text to speech."""
    try:
        def run_speech():
            engine.say(text)
            engine.runAndWait()
        Thread(target=run_speech).start()
        return text
    except Exception as e:
        logger.error(f"Error in speak: {e}")
        return f"Speech error: {e}"

def normalize_shortcut(shortcut):
    """Normalizes key terms in shortcuts to match keyboard library conventions."""
    replacements = {
        'control': 'ctrl', 'option': 'alt', 'windows': 'win', 'spacebar': 'space',
        'shift': 'shift', 'tab': 'tab', 'enter': 'enter', 'escape': 'esc',
        'delete': 'delete', 'insert': 'insert', 'home': 'home', 'end': 'end',
        'pageup': 'pgup', 'pagedown': 'pgdn', 'arrowup': 'up', 'arrowdown': 'down',
        'arrowleft': 'left', 'arrowright': 'right',
    }
    for old, new in replacements.items():
        shortcut = shortcut.replace(old, new)
    return shortcut

def open_application(app_name):
    try:
        open(app_name, match_closest=True)
        return speak(f"Opening {app_name}")
    except Exception as e:
        return speak(f"Sorry, I couldn't open {app_name}: {e}")

def close_application(app_name):
    try:
        close(app_name, match_closest=True)
        return speak(f"Closing {app_name}")
    except Exception as e:
        return speak(f"Failed to close {app_name}: {e}")

def close_all_applications():
    speak("Closing non-critical applications...")
    try:
        command = (
            'Get-Process | '
            'Where-Object { $_.MainWindowTitle -ne "" -and $_.ProcessName -notlike "*explorer*" } | '
            'Stop-Process -Force'
        )
        result = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True)
        if result.returncode:
            return speak(f"Some applications couldn't close: {result.stderr}")
        return speak("Most applications closed.")
    except Exception as e:
        return speak(f"Failed to close applications: {e}")

def get_system_info():
    try:
        info = subprocess.check_output("systeminfo").decode('utf-8')
        return speak(info)
    except Exception as e:
        return speak(f"Couldn't fetch system info: {e}")

def shutdown_system():
    speak("Shutting down in 1 second...")
    os.system("shutdown /s /t 1")
    return "System shutdown initiated"

def restart_system():
    speak("Restarting in 1 second...")
    os.system("shutdown /r /t 1")
    return "System restart initiated"

def sleep_system():
    speak("Putting system to sleep...")
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    return "System put to sleep"

def lock_computer():
    speak("Locking the computer...")
    ctypes.windll.user32.LockWorkStation()
    return "Computer locked"

def set_reminder(reminder, time_str):
    try:
        current_time = datetime.datetime.now()
        reminder_time = datetime.datetime.strptime(time_str, "%H:%M").replace(
            year=current_time.year, month=current_time.month, day=current_time.day
        )
        time_delta = (reminder_time - current_time).total_seconds()
        if time_delta > 0:
            def remind():
                time.sleep(time_delta)
                speak(f"Reminder: {reminder}")
            Thread(target=remind).start()
            return speak(f"Reminder set for {time_str}")
        return speak("Time has passed. Try again.")
    except ValueError:
        return speak("Invalid time format.")

def get_weather():
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    complete_url = f"{base_url}?q={CITY_NAME}&appid={WEATHER_API_KEY}&units=metric"
    try:
        response = requests.get(complete_url)
        weather_data = response.json()
        if response.status_code == 200:
            main = weather_data["main"]
            description = weather_data["weather"][0]["description"]
            return speak(f"Weather in {CITY_NAME}: {main['temp']}°C, {main['humidity']}% humidity. {description.capitalize()}.")
        return speak("Weather data unavailable.")
    except Exception as e:
        return speak(f"Weather check failed: {e}")

def control_media(command):
    if "play" in command:
        os.system("start wmplayer")
        return speak("Playing media.")
    elif "pause" in command:
        os.system("pause")
        return speak("Media paused.")
    elif "stop" in command:
        os.system("stop")
        return speak("Media stopped.")
    return speak("Unknown media command.")

def search_web(query):
    try:
        webbrowser.open(f"https://www.google.com/search?q={query}")
        return speak(f"Searching: {query}")
    except Exception as e:
        return speak(f"Web search failed: {e}")

def get_wikipedia_info(query):
    try:
        result = wikipedia.summary(query, sentences=2)
        return speak(f"Wikipedia says: {result}")
    except wikipedia.exceptions.DisambiguationError:
        return speak("Multiple results found. Please be more specific.")
    except wikipedia.exceptions.PageError:
        return speak("No information found on that topic.")

def send_email(to, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to, msg.as_string())
        return speak("Email sent successfully.")
    except smtplib.SMTPAuthenticationError:
        return speak("Email failed. Check your app password settings.")
    except Exception as e:
        return speak(f"Email failed: {e}")

def get_news():
    base_url = "https://newsapi.org/v2/top-headlines"
    complete_url = f"{base_url}?country=us&apiKey={NEWS_API_KEY}"
    try:
        response = requests.get(complete_url)
        news_data = response.json()
        if response.status_code == 200:
            for idx, article in enumerate(news_data["articles"][:5], 1):
                speak(f"News {idx}: {article['title']}")
                time.sleep(1)
            return "Latest news provided"
        return speak("News update failed.")
    except Exception as e:
        return speak(f"News update failed: {e}")

def answer_question(query):
    if "what is your name" in query:
        return speak("I'm Zeeko, your virtual assistant.")
    elif "how are you" in query:
        return speak("I'm doing great!")
    elif "what can you do" in query:
        return speak("I can help with emails, reminders, system control, web searches, and more!")
    elif "time" in query:
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        return speak(f"The time is {current_time}")
    elif "date" in query:
        current_date = datetime.datetime.now().strftime("%B %d, %Y")
        return speak(f"Today's date is {current_date}")
    else:
        speak("I'm not sure. Let me try searching the web...")
        return search_web(query)

def make_call(number):
    try:
        webbrowser.open(f"tel:{number}")
        return speak(f"Calling {number}...")
    except Exception as e:
        return speak(f"Call failed: {e}")

def take_photo():
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return speak("Camera not accessible.")
        ret, frame = cap.read()
        if ret:
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"{MEDIA_FOLDER}/photo_{timestamp}.jpg"
            cv2.imwrite(filename, frame)
            cap.release()
            return speak(f"Photo saved as {filename}")
        cap.release()
        return speak("Failed to capture photo.")
    except Exception as e:
        return speak(f"Error taking photo: {e}")

def record_video(duration=10):
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return speak("Camera not accessible.")
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{MEDIA_FOLDER}/video_{timestamp}.avi"
        out = cv2.VideoWriter(filename, fourcc, 20.0, (640, 480))
        start_time = time.time()
        record_time = 0
        while record_time < duration:
            ret, frame = cap.read()
            if ret:
                out.write(frame)
            record_time = time.time() - start_time
        cap.release()
        out.release()
        return speak(f"Video saved as {filename}")
    except Exception as e:
        return speak(f"Error recording video: {e}")

def go_to_desktop():
    try:
        ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)  # LWIN down
        time.sleep(0.1)
        ctypes.windll.user32.keybd_event(0x44, 0, 0, 0)  # D down
        time.sleep(0.1)
        ctypes.windll.user32.keybd_event(0x44, 0, 2, 0)  # D up
        time.sleep(0.1)
        ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)  # LWIN up
        return speak("Returned to desktop.")
    except Exception as e:
        return speak(f"Failed to go to desktop: {e}")

def get_time_greeting():
    current_hour = datetime.datetime.now().hour
    if 5 <= current_hour < 12:
        return f"Good morning, {BOSS_WORD}! How can I assist you today?"
    elif 12 <= current_hour < 16:
        return f"Good afternoon, {BOSS_WORD}! How can I assist you today?"
    elif 16 <= current_hour < 20:
        return f"Good evening, {BOSS_WORD}! How can I assist you today?"
    return f"Hello, {BOSS_WORD}! It's late. How can I assist you today?"

def delete_temp_files():
    try:
        command = "del /q /f /s %TEMP%\\*"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return speak("Temporary files deleted successfully.")
        return speak(f"Failed to delete temporary files. Error: {result.stderr}")
    except Exception as e:
        return speak(f"Error deleting temporary files: {e}")

def tell_joke():
    joke = pyjokes.get_joke()
    return speak(joke)

def translate_text(text, target_language="es"):
    try:
        translator.to_lang = target_language
        translation = translator.translate(text)
        return speak(f"Translation: {translation}")
    except Exception as e:
        return speak(f"Translation failed: {e}")

def solve_math_problem(question):
    try:
        client = wolframalpha.Client(WOLFRAM_APP_ID)
        res = client.query(question)
        answer = next(res.results).text
        return speak(f"The answer is: {answer}")
    except Exception as e:
        return speak(f"Couldn't solve that: {e}")

def manage_calendar(event_details):
    return speak("Calendar integration is coming soon!")

def send_whatsapp_message(number, message):
    return speak("WhatsApp integration is coming soon!")

def create_file(filename):
    try:
        if not filename:
            return speak("Please specify a filename.")
        if os.path.exists(filename):
            return speak(f"File {filename} already exists.")
        with open(filename, 'w') as f:
            f.write("")
        return speak(f"File {filename} created successfully.")
    except Exception as e:
        return speak(f"Error creating file: {e}")

def delete_file(filename):
    try:
        if not filename:
            return speak("Please specify a filename.")
        if not os.path.exists(filename):
            return speak(f"File {filename} does not exist.")
        os.remove(filename)
        return speak(f"File {filename} deleted successfully.")
    except Exception as e:
        return speak(f"Error deleting file: {e}")

def rename_file(old_name, new_name):
    try:
        if not old_name or not new_name:
            return speak("Please specify both old and new filenames.")
        if not os.path.exists(old_name):
            return speak(f"File {old_name} does not exist.")
        os.rename(old_name, new_name)
        return speak(f"File {old_name} renamed to {new_name} successfully.")
    except Exception as e:
        return speak(f"Error renaming file: {e}")

def connect_to_network(network_name):
    try:
        result = subprocess.run(
            ['netsh', 'wlan', 'connect', 'name=' + network_name],
            capture_output=True, text=True
        )
        if "connected" in result.stdout.lower():
            return speak(f"Connected to {network_name} successfully.")
        return speak(f"Failed to connect to {network_name}.")
    except Exception as e:
        return speak(f"Error connecting to network: {e}")

def disconnect_from_network(network_name):
    try:
        result = subprocess.run(
            ['netsh', 'wlan', 'disconnect'],
            capture_output=True, text=True
        )
        if "disconnected" in result.stdout.lower():
            return speak(f"Disconnected from {network_name} successfully.")
        return speak(f"Failed to disconnect from {network_name}.")
    except Exception as e:
        return speak(f"Error disconnecting from network: {e}")

def check_internet_speed():
    try:
        st = speedtest.Speedtest()
        download = st.download() / 1_000_000  # Convert to Mbps
        upload = st.upload() / 1_000_000
        return speak(f"Your download speed is {download:.2f} Mbps and your upload speed is {upload:.2f} Mbps.")
    except Exception as e:
        return speak(f"Error checking internet speed: {e}")

def handle_question(query):
    """Handles different types of questions and generates summaries."""
    response = ""
    summary = ""
    
    # Yes/No Questions
    if query.startswith(("is ", "are ", "can ", "does ", "do ")):
        if "your name" in query:
            response = speak("Yes, I am Zeeko, your assistant.")
            summary = "Confirmed identity as Zeeko."
        elif "weather" in query:
            response = get_weather()
            summary = f"Provided weather status for {CITY_NAME}."
        else:
            response = speak("I can try to find out!")
            search_web(query)
            summary = f"Searched web for: {query}"
    
    # What Questions
    elif query.startswith("what"):
        if "time" in query:
            current_time = datetime.datetime.now().strftime("%I:%M %p")
            response = speak(f"The time is {current_time}")
            summary = f"Reported current time: {current_time}"
        elif "date" in query:
            current_date = datetime.datetime.now().strftime("%B %d, %Y")
            response = speak(f"Today's date is {current_date}")
            summary = f"Reported current date: {current_date}"
        elif "weather" in query:
            response = get_weather()
            summary = f"Provided weather info for {CITY_NAME}"
        else:
            response = get_wikipedia_info(query.replace("what ", "").replace("is ", ""))
            summary = f"Provided Wikipedia info for: {query}"
    
    # How Questions
    elif query.startswith("how"):
        if "are you" in query:
            response = speak("I'm doing great, thanks for asking!")
            summary = "Expressed well-being status."
        elif "to" in query:
            response = solve_math_problem(query)
            summary = f"Explained how to solve: {query}"
        else:
            response = search_web(query)
            summary = f"Searched how-to for: {query}"
    
    # When Questions
    elif query.startswith("when"):
        if "time" in query:
            response = speak(f"It's {datetime.datetime.now().strftime('%I:%M %p')} right now.")
            summary = "Reported current time."
        else:
            response = get_wikipedia_info(query.replace("when ", ""))
            summary = f"Provided historical info for: {query}"
    
    # Where Questions
    elif query.startswith("where"):
        if "am i" in query:
            response = speak(f"You're in {CITY_NAME}, I assume!")
            summary = f"Assumed location as {CITY_NAME}"
        else:
            response = search_web(query)
            summary = f"Searched location for: {query}"
    
    # Why Questions
    elif query.startswith("why"):
        response = get_wikipedia_info(query.replace("why ", ""))
        summary = f"Explained reason for: {query}"
    
    # Default
    else:
        response = answer_question(query)
        summary = f"Answered general question: {query}"
    
    return response, summary

@app.route('/')
def serve_frontend():
    try:
        logger.info("Serving index.html")
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        logger.error(f"Error serving frontend: {e}")
        return "Error serving page", 500

@app.route('/api/ask', methods=['POST'])
def ask():
    global summaries
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'response': 'Please provide a query.'}), 400
        query = data['query'].lower().strip()
        logger.info(f"Received query: {query}")

        response = ""
        if any(phrase in query for phrase in ["exit", "quit", "bye"]):
            response = speak("Shutting down. Goodbye!")
            if summaries:
                final_summary = "Final summary of our session:\n" + "\n".join([f"{i}. {s}" for i, s in enumerate(summaries, 1)])
                speak(final_summary)
            summaries = []
        
        elif any(phrase in query for phrase in ["close all apps and shut down","close all app","close all apps","close all applications ","close all application", "shut down after closing apps", "close everything and turn off"]):
            summaries.append(close_all_applications())
            summaries.append(shutdown_system())
            response = "Closed apps and initiated shutdown."
        
        elif any(phrase in query for phrase in ["back to desktop", "go back", "home screen"]):
            response = go_to_desktop()
            summaries.append(response)
        
        elif 'open' in query:
            app_name = query.replace('open ', '').strip()
            response = open_application(app_name)
            summaries.append(response)
        
        elif 'close all' in query or 'close all apps' in query:
            response = close_all_applications()
            summaries.append(response)
        
        elif 'close' in query:
            app_name = query.replace('close ', '').strip()
            response = close_application(app_name)
            summaries.append(response)
        
        elif 'system info' in query:
            response = get_system_info()
            summaries.append(response)
        
        elif 'search' in query:
            search_query = query.replace('search ', '').strip()
            response = search_web(search_query)
            summaries.append(response)
        
        elif 'shutdown' in query or 'turn off' in query:
            response = shutdown_system()
            summaries.append(response)
        
        elif 'restart' in query:
            response = restart_system()
            summaries.append(response)
        
        elif 'sleep' in query:
            response = sleep_system()
            summaries.append(response)
        
        elif 'lock screen' in query:
            response = lock_computer()
            summaries.append(response)
        
        elif 'reminder' in query:
            reminder = data.get('reminder', 'Reminder')
            time_str = data.get('time', '12:00')
            response = set_reminder(reminder, time_str)
            summaries.append(response)
        
        elif 'weather' in query:
            response = get_weather()
            summaries.append(response)
        
        elif query.startswith("press "):
            shortcut = query[6:].strip()
            if not shortcut:
                response = speak("Please specify a key or shortcut to press.")
            else:
                normalized_shortcut = normalize_shortcut(shortcut)
                try:
                    keyboard.send(normalized_shortcut)
                    response = speak(f"Shortcut {normalized_shortcut} executed.")
                except:
                    response = speak(f"Error executing {shortcut}.")
            summaries.append(response)
        
        elif query.startswith("type "):
            text = query[5:].strip()
            if not text:
                response = speak("Please specify text to type.")
            else:
                try:
                    keyboard.write(text)
                    response = speak(f"Typed: {text}")
                except:
                    response = speak(f"Error typing {text}.")
            summaries.append(response)
        
        elif 'wikipedia' in query:
            search_query = query.replace('wikipedia ', '').strip()
            response = get_wikipedia_info(search_query)
            summaries.append(response)
        
        elif 'email' in query or 'mail' in query:
            to = data.get('to', 'test@example.com')
            subject = data.get('subject', 'Test Email')
            body = data.get('body', 'Hello from Zeeko!')
            response = send_email(to, subject, body)
            summaries.append(response)
        
        elif 'news' in query:
            response = get_news()
            summaries.append(response)
        
        elif 'call' in query:
            number = query.replace('call ', '').strip()
            response = make_call(number)
            summaries.append(response)
        
        elif 'take photo' in query:
            response = take_photo()
            summaries.append(response)
        
        elif 'record video' in query:
            duration = int(data.get('duration', 10))
            response = record_video(duration)
            summaries.append(response)
        
        elif any(phrase in query for phrase in ["temp files", "clear temporary files", "clean temp files", "remove temp files"]):
            response = delete_temp_files()
            summaries.append(response)
        
        elif 'joke' in query:
            response = tell_joke()
            summaries.append(response)
        
        elif 'translate' in query:
            text = data.get('text', 'Hello')
            target_language = data.get('lang', 'es')
            response = translate_text(text, target_language)
            summaries.append(response)
        
        elif 'math' in query or 'calculate' in query:
            problem = query.replace('math ', '').replace('calculate ', '')
            response = solve_math_problem(problem)
            summaries.append(response)
        
        elif 'calendar' in query:
            event_details = data.get('event', 'Event')
            response = manage_calendar(event_details)
            summaries.append(response)
        
        elif 'whatsapp' in query:
            number = data.get('number', '1234567890')
            message = data.get('message', 'Hello from Zeeko!')
            response = send_whatsapp_message(number, message)
            summaries.append(response)
        
        elif 'create file' in query:
            filename = data.get('filename', 'newfile.txt')
            response = create_file(filename)
            summaries.append(response)
        
        elif 'delete file' in query:
            filename = data.get('filename', 'newfile.txt')
            response = delete_file(filename)
            summaries.append(response)
        
        elif 'rename file' in query:
            old_name = data.get('old_name', 'oldfile.txt')
            new_name = data.get('new_name', 'newfile.txt')
            response = rename_file(old_name, new_name)
            summaries.append(response)
        
        elif 'connect to network' in query:
            network_name = data.get('network', 'MyNetwork')
            response = connect_to_network(network_name)
            summaries.append(response)
        
        elif 'disconnect from network' in query:
            network_name = data.get('network', 'MyNetwork')
            response = disconnect_from_network(network_name)
            summaries.append(response)
        
        elif 'check internet speed' in query:
            response = check_internet_speed()
            summaries.append(response)
        
        elif any(q in query for q in ["is ", "are ", "can ", "does ", "do ", "what", "how", "when", "where", "why"]):
            response, summary = handle_question(query)
            summaries.append(summary)
        
        elif 'summary' in query:
            if summaries:
                response = "Here's what we've done:\n" + "\n".join([f"{i}. {s}" for i, s in enumerate(summaries, 1)])
                speak(response)
            else:
                response = speak("No activities to summarize yet!")
        
        else:
            response = answer_question(query)
            summaries.append(response)

        return jsonify({'response': response})
    except Exception as e:
        logger.error(f"Error in /api/ask: {e}")
        return jsonify({'response': f"Server error: {e}"}), 500

if __name__ == '__main__':
    try:
        logger.info("Starting Flask server...")
        speak("Initializing Zeeko...")
        greeting = get_time_greeting()
        speak(f"{greeting} Current date: {datetime.datetime.now().strftime('%B %d, %Y')}")
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")