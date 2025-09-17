from pymongo import  ReturnDocument
from pyrogram.enums import ChatMemberStatus, ChatType
from shivu import user_totals_collection, shivuu, sudo_users
from pyrogram import Client, filters
from pyrogram.types import Message


@shivuu.on_message(filters.command("changetime"))
async def change_time(client: Client, message: Message):
    
    user_id = message.from_user.id
    chat_id = message.chat.id
        
    # Check if user is a sudo user (not just group admin)
    if str(user_id) not in sudo_users:
        await message.reply_text('🚫 This command is only available to bot administrators.')
        return

    try:
        args = message.command
        if len(args) != 2:
            await message.reply_text('Please use: /changetime NUMBER')
            return

        new_frequency = int(args[1])
        # Allow sudo users to set any frequency (including below 100)
        if new_frequency < 1:
            await message.reply_text('The message frequency must be at least 1.')
            return

    
        chat_frequency = await user_totals_collection.find_one_and_update(
            {'chat_id': str(chat_id)},
            {'$set': {'message_frequency': new_frequency}},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

        await message.reply_text(f'Successfully changed {new_frequency}')
    except Exception as e:
        await message.reply_text(f'Failed to change {str(e)}')
