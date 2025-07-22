# Yogi

Yogi is a Python-based project designed for voice interaction, automation, and assistant functionalities. The project is modular and extensible, supporting various tools and APIs for voice processing and automation tasks.

## Project Structure

- `agent.py` - Main agent logic for Yogi.
- `api.py` - (Empty) Placeholder for API endpoints or integrations.
- `prompts.py` - Contains prompt templates or logic for customizing Yogi's behavior and personality.
- `tools.py` - Utility functions and tools used by Yogi.
- `requirements.txt` - Python dependencies for the project.
- `todo.json` - Task tracking in JSON format.
- `notes.json` - Project notes and metadata.

## Features

- **Voice interaction** with Google LLM and noise cancellation
- **Weather fetching** (via wttr.in)
- **Web search** (DuckDuckGo)
- **Email sending** (Gmail SMTP, credentials from `.env`)
- **To-do list** (add, list, clear tasks, stored in `todo.json`)
- **File search and reading** (with natural language path inference)
- **Notes management** (write and show notes, stored in `notes.json`)
- **Password generator** (secure, customizable length)
- **System information** (CPU, RAM, disk usage)
- **Math solver** (symbolic and arithmetic expressions)
- **Wikipedia summary** (fetches summaries for topics)
- **News headlines** (fetches latest headlines from free sources)
- **Joke or quote of the day** (random joke or inspirational quote)
- **Currency conversion** (using exchangerate.host)
- **Unit conversion** (using pint)
- **Timer/alarm** (set timers, get notified)
- **Google Calendar integration** (view and add events; OAuth2 setup required)
- **Customizable prompts and behavior** via `prompts.py` (easily tailor Yogi's personality and responses)

## Setup Instructions

1. **Clone the repository:**
   ```sh
   git clone <your-repo-url>
   cd Yogi
   ```
2. **Create and activate a virtual environment:**
   ```sh
   python -m venv voice_env
   # On Windows:
   .\voice_env\Scripts\activate
   # On Unix or MacOS:
   source voice_env/bin/activate
   ```
3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
4. **Set up environment variables:**
   - Create a `.env` file with your Gmail credentials for email sending:
     ```env
     gmail_user=your_email@gmail.com
     gmail_password=your_app_password (this is not the same as your gmail account password)
     ```
5. **Google Calendar Integration (OAuth2):**
   - Download your Google OAuth2 client credentials as a JSON file (e.g., `client_secret_...json`).
   - Place the file in the project root.
   - On first use, Yogi will prompt you to log in via a browser to authorize access. This is a one-time setup; credentials are saved in `token.pickle` for future use.
   - **Note:** You must enable the Google Calendar API in your Google Cloud project.

## Security & Data Protection

- **Sensitive files** such as `.env`, `notes.json`, `todo.json`, logs, and virtual environments are excluded from version control via `.gitignore`.
- **Never commit API keys, credentials, or personal data** to the repository.
- Review `.gitignore` regularly to ensure new sensitive files are not tracked.

## Contributing

1. Fork the repository.
2. Create a new branch for your feature or bugfix.
3. Submit a pull request with a clear description of your changes.

## License

Specify your license here (e.g., MIT, Apache 2.0, etc.). 