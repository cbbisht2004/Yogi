import asyncio
from tools import get_calendar_events

# Dummy context, since your function expects a context argument but doesn't use it
class DummyContext:
    pass

async def main():
    # You can change the number of days as needed
    result = await get_calendar_events(DummyContext(), days=10)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())