import os, asyncio
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioVideoPiped

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
SESSION_STRING = os.getenv('SESSION_STRING')

userbot = Client(
    "helper_session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

pytgcalls_client = PyTgCalls(userbot)

async def main():
    await userbot.start()
    await pytgcalls_client.start()
    print("✅ جاهز! أرسل ID الجروب:")
    group_id = int(input("Group ID: "))
    print("أرسل مسار الفيديو:")
    video_path = input("Video path: ")
    await pytgcalls_client.join_group_call(
        group_id,
        AudioVideoPiped(video_path)
    )
    print("✅ تم فتح الكول!")
    await asyncio.sleep(999999)

asyncio.run(main())
