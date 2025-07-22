import logging
import secrets
import string
import smtplib
import requests
import os
import json
from typing import Optional, Tuple
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import psutil
import sympy
import wikipedia
import pint
import time
import threading
import datetime
import pytz
from sympy import sympify
from pint import UnitRegistry

# For news and jokes/quotes
import random

# For Google Calendar
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

# For currency conversion
# We'll use exchangerate.host (no API key required)

from livekit.agents import function_tool, RunContext
from langchain_community.tools import DuckDuckGoSearchRun

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Windows-safe path handling
TODO_FILE = os.path.join(os.getcwd(), "todo.json")

def load_tasks():
    """Load tasks from todo.json"""
    if not os.path.exists(TODO_FILE):
        logging.debug(f"[DEBUG] No todo.json found at {TODO_FILE}, starting fresh.")
        return []
    try:
        with open(TODO_FILE, "r", encoding="utf-8") as f:
            tasks = json.load(f)
            logging.debug(f"[DEBUG] Loaded tasks: {tasks}")
            return tasks
    except json.JSONDecodeError as e:
        logging.error(f"[ERROR] JSON decode error: {e}, resetting todo.json.")
        save_tasks([])  # Reset the file to an empty list
        return []
    except Exception as e:
        logging.error(f"[ERROR] Failed to read {TODO_FILE}: {e}")
        return []

def save_tasks(tasks):
    """Save tasks to todo.json"""
    try:
        with open(TODO_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)
            logging.debug(f"[DEBUG] Saved tasks: {tasks}")
    except Exception as e:
        logging.error(f"[ERROR] Failed to save tasks: {e}")

@function_tool()
async def get_weather(context: RunContext, city: str) -> str:
    """Get current weather for a city."""
    try:
        response = requests.get(f"http://wttr.in/{city}?format=3")
        if response.status_code == 200:
            return response.text.strip()
        else:
            logging.error(f"[ERROR] Weather fetch failed with status: {response.status_code}")
            return f"Couldn't fetch weather for {city}."
    except Exception as e:
        logging.error(f"[ERROR] Exception in get_weather: {e}")
        return f"Couldn't fetch weather for {city}."

@function_tool()
async def search_web(context: RunContext, query: str) -> str:
    """Search the web using DuckDuckGo."""
    try:
        results = DuckDuckGoSearchRun().run(tool_input=query)
        logging.info(f"[INFO] Search results for '{query}': {results}")
        return results
    except Exception as e:
        logging.error(f"[ERROR] Search error: {e}")
        return f"Could not perform search for '{query}'."

@function_tool()
async def send_email(context: RunContext, to_email: str, subject: str, message: str, cc_email: Optional[str] = None) -> str:
    """Send an email via Gmail SMTP."""
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        gmail_user = os.getenv("gmail_user")
        gmail_password = os.getenv("gmail_password")

        if not gmail_user or not gmail_password:
            logging.error("[ERROR] Gmail credentials missing.")
            return "Gmail credentials not set in environment."

        msg = MIMEMultipart()
        msg["From"] = gmail_user
        msg["To"] = to_email
        msg["Subject"] = subject

        recipients = [to_email]
        if cc_email:
            msg["Cc"] = cc_email
            recipients.append(cc_email)

        msg.attach(MIMEText(message, "plain"))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, recipients, msg.as_string())
        server.quit()

        logging.info(f"[INFO] Email sent to {recipients}")
        return f"Email sent to {to_email}."
    except smtplib.SMTPAuthenticationError as e:
        logging.error(f"[ERROR] SMTP Auth Error: {e}")
        return "Authentication with SMTP failed."
    except Exception as e:
        logging.error(f"[ERROR] Failed to send email: {e}")
        return "Failed to send the email."

@function_tool()
async def add_task(context: RunContext, task: str) -> str:
    """Add a task to the to-do list."""
    tasks = load_tasks()
    tasks.append(task)
    save_tasks(tasks)
    return f"Task added: {task}"

@function_tool()
async def list_tasks(context: RunContext) -> str:
    """List all to-do tasks."""
    tasks = load_tasks()
    if not tasks:
        return "No tasks in the list."
    return "\n".join(f"{i+1}. {t}" for i, t in enumerate(tasks))

@function_tool()
async def clear_tasks(context: RunContext) -> str:
    """Clear all to-do tasks."""
    save_tasks([])
    return "All tasks cleared."


def infer_path_from_natural_language(nl_path: str) -> str:
    """Convert common English folder phrases to actual Windows paths."""
    nl_path = nl_path.lower().strip()
    userprofile = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    mappings = {
        "my documents": os.path.join(userprofile, "Documents"),
        "documents folder": os.path.join(userprofile, "Documents"),
        "downloads folder": os.path.join(userprofile, "Downloads"),
        "my downloads": os.path.join(userprofile, "Downloads"),
        "desktop": os.path.join(userprofile, "Desktop"),
        "pictures folder": os.path.join(userprofile, "Pictures"),
        "music folder": os.path.join(userprofile, "Music"),
        "videos folder": os.path.join(userprofile, "Videos"),
        "c drive": "C:\\",
        "d drive": "D:\\",
        "root": os.path.abspath(os.sep),
        "home": userprofile,
        "user folder": userprofile,
        "documents": os.path.join(userprofile, "Documents"),
        "downloads": os.path.join(userprofile, "Downloads"),
        "pictures": os.path.join(userprofile, "Pictures"),
        "music": os.path.join(userprofile, "Music"),
        "videos": os.path.join(userprofile, "Videos"),
    }
    for key, val in mappings.items():
        if key in nl_path:
            return val
    # If user says e.g. "c drive in the documents folder"
    if "c drive" in nl_path and "documents" in nl_path:
        return os.path.join("C:\\", "Users", os.getlogin(), "Documents")
    if "d drive" in nl_path and "documents" in nl_path:
        return os.path.join("D:\\", "Users", os.getlogin(), "Documents")
    # Fallback: return as-is
    return nl_path

def is_text_file(filepath: str, blocksize: int = 512) -> bool:
    """Check if a file is likely a text file."""
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(blocksize)
            if b'\0' in chunk:
                return False
            # Try decoding as utf-8
            try:
                chunk.decode('utf-8')
                return True
            except UnicodeDecodeError:
                return False
    except Exception as e:
        logging.error(f"[ERROR] Could not check file type: {e}")
        return False


def find_file(filename: str, search_dir: str = ".", max_depth: int = 5) -> Tuple[str, str]:
    """Find a file by name within a directory up to a certain depth. Returns (full_path, root) or (None, None) if not found."""
    search_dir = os.path.abspath(search_dir)
    for root, _, files in os.walk(search_dir):
        # Calculate depth
        rel_path = os.path.relpath(root, search_dir)
        depth = rel_path.count(os.sep)
        if depth > max_depth:
            continue
        if filename in files:
            return os.path.join(root, filename), root
    return None, None

@function_tool()
async def find_and_read_file(context: RunContext, filename: str, search_dir: str = ".", max_depth: int = 5, confirm: bool = False) -> str:
    """Find a file by name and return its contents. Accepts natural language for search_dir. Optionally limits search depth. Asks for confirmation before reading. Handles binary files gracefully."""
    resolved_dir = infer_path_from_natural_language(search_dir)
    file_path, found_root = find_file(filename, resolved_dir, max_depth)
    if not file_path:
        return f"File '{filename}' not found in '{resolved_dir}' (searched up to depth {max_depth})."
    # Ask for confirmation if not already confirmed
    if not confirm:
        return (f"File found: {file_path}\n\nDo you want to read this file? "
                f"If yes, call this tool again with 'confirm=True'.")
    # Check if file is text
    if not is_text_file(file_path):
        return f"File '{file_path}' appears to be binary or not a text file. Reading as text is not supported."
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Limit output size for very large files
            if len(content) > 4000:
                return f"File '{file_path}' is too large to display in full. Showing first 4000 characters:\n\n{content[:4000]}"
            return f"File found: {file_path}\n\n{content}"
    except Exception as e:
        return f"Error reading file {file_path}: {e}"


# Persistent notes store
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOTES_FILE = os.path.join(BASE_DIR, "notes.json")

def load_notes():
    """Load notes from notes.json"""
    if not os.path.exists(NOTES_FILE):
        logging.debug(f"[DEBUG] No notes.json found at {NOTES_FILE}, starting fresh.")
        return []
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            notes = json.load(f)
            logging.debug(f"[DEBUG] Loaded notes: {notes}")
            return notes
    except json.JSONDecodeError as e:
        logging.error(f"[ERROR] JSON decode error: {e}, resetting notes.json.")
        save_notes([])  # Reset the file to an empty list
        return []
    except Exception as e:
        logging.error(f"[ERROR] Failed to read {NOTES_FILE}: {e}")
        return []

def save_notes(notes):
    try:
        with open(NOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(notes, f, indent=2, ensure_ascii=False)
            logging.debug(f"[DEBUG] Saved notes: {notes}")
    except Exception as e:
        logging.error(f"[ERROR] Failed to save notes: {e}")

@function_tool()
async def write_note(context: RunContext, note: str) -> str:
    """Append new info to the last note, or create a new note if none exist."""
    notes = load_notes()
    if notes:
        notes[-1] = notes[-1].rstrip() + "\n" + note.lstrip()
        logging.debug(f"[DEBUG] Appended to last note: {note}")
        msg = "Note updated."
    else:
        notes.append(note)
        logging.debug(f"[DEBUG] Note added: {note}")
        msg = "Note added."
    save_notes(notes)
    return msg

@function_tool()
async def show_notes(context: RunContext) -> str:
    """Show all notes."""
    notes = load_notes()
    return "\n".join(f"{i+1}. {n}" for i, n in enumerate(notes)) or "No notes saved."

@function_tool()
async def generate_password(context: RunContext, length: int = 12) -> str:
    """Generate a secure password."""
    if length < 6:
        return "Password must be at least 6 characters long."
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(characters) for _ in range(length))
    logging.debug(f"[DEBUG] Generated password: {password}")
    return password

# --- SYSTEM INFORMATION ---
@function_tool()
async def get_system_info(context: RunContext) -> str:
    """Get system information: CPU, RAM, and disk usage."""
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return (f"CPU Usage: {cpu}%\n"
                f"RAM Usage: {ram.percent}% ({ram.used // (1024**2)}MB/{ram.total // (1024**2)}MB)\n"
                f"Disk Usage: {disk.percent}% ({disk.used // (1024**3)}GB/{disk.total // (1024**3)}GB)")
    except Exception as e:
        return f"Error getting system info: {e}"

# --- MATH SOLVER ---
@function_tool()
async def solve_math(context: RunContext, expression: str) -> str:
    """Solve a math expression or equation."""
    try:
        result = sympify(expression)
        return f"Result: {result}"
    except Exception as e:
        return f"Error solving math: {e}"

# --- WIKIPEDIA SUMMARY ---
@function_tool()
async def wikipedia_summary(context: RunContext, topic: str, sentences: int = 2) -> str:
    """Get a summary of a Wikipedia topic."""
    try:
        summary = wikipedia.summary(topic, sentences=sentences)
        return summary
    except wikipedia.DisambiguationError as e:
        return f"Topic is ambiguous. Options: {e.options[:5]}..."
    except wikipedia.PageError:
        return "Topic not found."
    except Exception as e:
        return f"Error fetching Wikipedia summary: {e}"

# --- NEWS HEADLINES ---
@function_tool()
async def get_news_headlines(context: RunContext, country: str = 'us', count: int = 5) -> str:
    """Get latest news headlines (top stories)."""
    try:
        import requests
        url = f'https://newsapi.org/v2/top-headlines?country={country}&pageSize={count}&apiKey=demo'
        # 'demo' API key is rate-limited; for real use, set your own key in .env
        response = requests.get(url)
        data = response.json()
        if data.get('status') != 'ok':
            return f"Error from news API: {data.get('message', 'Unknown error')}"
        headlines = [article['title'] for article in data['articles'][:count]]
        return '\n'.join(headlines) if headlines else 'No headlines found.'
    except Exception as e:
        return f"Error fetching news: {e}"

# --- JOKE OR QUOTE OF THE DAY ---
@function_tool()
async def get_joke_or_quote(context: RunContext, type: str = 'joke') -> str:
    """Get a random joke or inspirational quote."""
    try:
        import requests
        if type == 'joke':
            resp = requests.get('https://official-joke-api.appspot.com/random_joke')
            if resp.status_code == 200:
                joke = resp.json()
                return f"{joke['setup']}\n{joke['punchline']}"
            else:
                return "Couldn't fetch a joke."
        else:
            resp = requests.get('https://api.quotable.io/random')
            if resp.status_code == 200:
                quote = resp.json()
                return f"{quote['content']} — {quote['author']}"
            else:
                return "Couldn't fetch a quote."
    except Exception as e:
        return f"Error fetching joke/quote: {e}"

# --- CURRENCY CONVERSION ---
@function_tool()
async def convert_currency(context: RunContext, amount: float, from_currency: str, to_currency: str) -> str:
    """Convert currency using exchangerate.host (no API key required)."""
    try:
        import requests
        url = f'https://api.exchangerate.host/convert?from={from_currency.upper()}&to={to_currency.upper()}&amount={amount}'
        resp = requests.get(url)
        data = resp.json()
        if data.get('success'):
            result = data['result']
            return f"{amount} {from_currency.upper()} = {result:.2f} {to_currency.upper()}"
        else:
            return f"Currency conversion failed: {data.get('error', 'Unknown error')}"
    except Exception as e:
        return f"Error converting currency: {e}"

# --- UNIT CONVERSION ---
ureg = UnitRegistry()
@function_tool()
async def convert_units(context: RunContext, value: float, from_unit: str, to_unit: str) -> str:
    """Convert between units (e.g., meters to feet, Celsius to Fahrenheit)."""
    try:
        q = ureg.Quantity(value, from_unit)
        result = q.to(to_unit)
        return f"{value} {from_unit} = {result.magnitude:.4g} {to_unit}"
    except Exception as e:
        return f"Error converting units: {e}"

# --- TIMER AND ALARM ---
# For a voice assistant, timers/alarms should notify the user asynchronously. We'll simulate with a thread and log.
@function_tool()
async def set_timer(context: RunContext, seconds: int) -> str:
    """Set a timer for a number of seconds. Notifies when time is up."""
    def timer_thread():
        time.sleep(seconds)
        logging.info(f"[TIMER] Timer for {seconds} seconds is up!")
    threading.Thread(target=timer_thread, daemon=True).start()
    return f"Timer set for {seconds} seconds."

# --- CALENDAR INTEGRATION (Google Calendar, read-only for demo) ---
@function_tool()
async def get_calendar_events(context: RunContext, days: int = None) -> str:
    """
    Interactively ask for number of days ahead to fetch Google Calendar events.
    If 'days' is None, the voice agent will ask the user first.
    Requires 'client_secret_*.json' and token.pickle for OAuth2.
    """

    # Ask the user if the time span is not provided
    if days is None:
        return "How many days ahead would you like to check your calendar events for?"

    # Proceed with authentication and event fetch
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    CLIENT_SECRET_FILE = 'client_secret_427246294712-lsoqfogqakf889pjer0bahhef62gg2fc.apps.googleusercontent.com(1).json'
    TOKEN_PICKLE = 'token.pickle'

    creds = None
    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PICKLE, 'wb') as token:
            pickle.dump(creds, token)

    try:
        service = build('calendar', 'v3', credentials=creds)
        import datetime
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        max_time = (datetime.datetime.utcnow() + datetime.timedelta(days=days)).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            timeMax=max_time,
            maxResults=20,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        if not events:
            return f'No upcoming events found in the next {days} day(s).'

        output = [f"Here are your events for the next {days} day(s):"]
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            output.append(f"{start}: {event['summary']}")
        return '\n'.join(output)

    except Exception as e:
        return f"Error fetching calendar events: {e}"

@function_tool()
async def add_calendar_event(
    context: RunContext,
    summary: str = None,
    start_time: str = None,
    end_time: str = None,
    description: str = ""
) -> str:
    """
    Add an event to Google Calendar. If any required info is missing, the voice agent will ask.
    Times must be in ISO 8601 format (e.g., '2025-07-22T23:45:00+05:30').
    """

    # Prompt for missing fields
    if not summary:
        return "What should I name the event?"

    if not start_time:
        return "When should the event start? (Please say in format like '2025-07-22T15:00:00+05:30')"

    if not end_time:
        return "When should the event end? (Please say in format like '2025-07-22T16:00:00+05:30')"

    # Google Calendar OAuth2 Setup
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    CLIENT_SECRET_FILE = 'client_secret_427246294712-lsoqfogqakf889pjer0bahhef62gg2fc.apps.googleusercontent.com(1).json'
    TOKEN_PICKLE = 'token.pickle'

    creds = None
    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PICKLE, 'wb') as token:
            pickle.dump(creds, token)

    try:
        service = build('calendar', 'v3', credentials=creds)

        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time
            },
            'end': {
                'dateTime': end_time
            }
        }

        created_event = service.events().insert(calendarId='primary', body=event).execute()

        return (
            f"✅ Event created successfully!\n"
            f"Title: {summary}\n"
            f"Start: {start_time}\n"
            f"End: {end_time}\n"
            f"Link: {created_event.get('htmlLink', 'N/A')}"
        )

    except Exception as e:
        return f"⚠️ Failed to add event: {e}"
