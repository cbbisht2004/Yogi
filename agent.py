from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import noise_cancellation, google
from prompts import AGENT_INSTRUCTIONS, SESSION_INSTRUCTIONS

# Import all tools from tools.py
from tools import (
    get_weather,
    send_email,
    search_web,
    add_task,
    list_tasks,
    clear_tasks,
    find_and_read_file,
    write_note,
    show_notes,
    generate_password,
    get_system_info,
    solve_math,
    wikipedia_summary,
    get_news_headlines,
    get_joke_or_quote,
    convert_currency,
    convert_units,
    set_timer,
    get_calendar_events,
    add_calendar_event,
)

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load .env variables (for Gmail credentials, etc.)
load_dotenv()

# Define your Assistant Agent
class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=AGENT_INSTRUCTIONS,
            llm=google.beta.realtime.RealtimeModel(
                voice="Charon",
                temperature=0.8,
            ),
            tools=[
                get_weather,
                send_email,
                search_web,
                add_task,
                list_tasks,
                clear_tasks,
                find_and_read_file,
                write_note,
                show_notes,
                generate_password,
                get_system_info,
                solve_math,
                wikipedia_summary,
                get_news_headlines,
                get_joke_or_quote,
                convert_currency,
                convert_units,
                set_timer,
                get_calendar_events,    
                add_calendar_event,
            ],
        )

# Define the entrypoint function
async def entrypoint(ctx: agents.JobContext):
    session = AgentSession()

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            video_enabled=True,
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()
    await session.generate_reply(instructions=SESSION_INSTRUCTIONS)

# Run the agent
if __name__ == "__main__":
    try:
        agents.cli.run_app(
            agents.WorkerOptions(entrypoint_fnc=entrypoint)
        )
    except Exception as e:
        logging.error(f"[ERROR] Failed to start agent: {e}")
