from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from shivu import user_collection, shivuu, collection
from shivu.config import Config

pending_trades = {}


@shivuu.on_message(filters.command("trade"))
async def trade(client, message):
    sender_id = message.from_user.id

    if not message.reply_to_message:
        await message.reply_text("You need to reply to a user's message to trade a character!")
        return

    receiver_id = message.reply_to_message.from_user.id

    if sender_id == receiver_id:
        await message.reply_text("You can't trade a character with yourself!")
        return

    if len(message.command) != 3:
        await message.reply_text("You need to provide two character IDs!")
        return

    sender_character_id, receiver_character_id = message.command[1], message.command[2]

    sender = await user_collection.find_one({'id': sender_id})
    receiver = await user_collection.find_one({'id': receiver_id})

    # Check if users exist and have characters field
    if not sender or not sender.get('characters'):
        await message.reply_text("You don't have any characters to trade!")
        return
        
    if not receiver or not receiver.get('characters'):
        await message.reply_text("The other user doesn't have any characters to trade!")
        return

    sender_character = next((character for character in sender['characters'] if character['id'] == sender_character_id), None)
    receiver_character = next((character for character in receiver['characters'] if character['id'] == receiver_character_id), None)

    if not sender_character:
        await message.reply_text("You don't have the character you're trying to trade!")
        return

    if not receiver_character:
        await message.reply_text("The other user doesn't have the character they're trying to trade!")
        return






    if len(message.command) != 3:
        await message.reply_text("/trade [Your Character ID] [Other User Character ID]!")
        return

    sender_character_id, receiver_character_id = message.command[1], message.command[2]

    
    pending_trades[(sender_id, receiver_id)] = (sender_character_id, receiver_character_id)

    
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Confirm Trade", callback_data="confirm_trade")],
            [InlineKeyboardButton("Cancel Trade", callback_data="cancel_trade")]
        ]
    )

    await message.reply_text(f"{message.reply_to_message.from_user.mention}, do you accept this trade?", reply_markup=keyboard)


@shivuu.on_callback_query(filters.create(lambda _, __, query: query.data in ["confirm_trade", "cancel_trade"]))
async def on_trade_callback_query(client, callback_query):
    receiver_id = callback_query.from_user.id

    
    for (sender_id, _receiver_id), (sender_character_id, receiver_character_id) in pending_trades.items():
        if _receiver_id == receiver_id:
            break
    else:
        await callback_query.answer("This is not for you!", show_alert=True)
        return

    if callback_query.data == "confirm_trade":
        
        sender = await user_collection.find_one({'id': sender_id})
        receiver = await user_collection.find_one({'id': receiver_id})

        # Check if users still exist and have characters
        if not sender or not sender.get('characters'):
            await callback_query.answer("Sender no longer has characters!", show_alert=True)
            return
            
        if not receiver or not receiver.get('characters'):
            await callback_query.answer("Receiver no longer has characters!", show_alert=True)
            return

        sender_character = next((character for character in sender['characters'] if character['id'] == sender_character_id), None)
        receiver_character = next((character for character in receiver['characters'] if character['id'] == receiver_character_id), None)

        if not sender_character or not receiver_character:
            await callback_query.answer("One of the characters is no longer available!", show_alert=True)
            return
        
        sender['characters'].remove(sender_character)
        receiver['characters'].remove(receiver_character)

        
        await user_collection.update_one({'id': sender_id}, {'$set': {'characters': sender['characters']}})
        await user_collection.update_one({'id': receiver_id}, {'$set': {'characters': receiver['characters']}})

        
        sender['characters'].append(receiver_character)
        receiver['characters'].append(sender_character)

        
        await user_collection.update_one({'id': sender_id}, {'$set': {'characters': sender['characters']}})
        await user_collection.update_one({'id': receiver_id}, {'$set': {'characters': receiver['characters']}})

        
        del pending_trades[(sender_id, receiver_id)]

        await callback_query.message.edit_text(f"You have successfully traded your character with {callback_query.message.reply_to_message.from_user.mention}!")

    elif callback_query.data == "cancel_trade":
        
        del pending_trades[(sender_id, receiver_id)]

        await callback_query.message.edit_text("❌️ Sad Cancelled....")




pending_gifts = {}


@shivuu.on_message(filters.command("gift"))
async def gift(client, message):
    sender_id = message.from_user.id

    if not message.reply_to_message:
        await message.reply_text("You need to reply to a user's message to gift a character!")
        return

    receiver_id = message.reply_to_message.from_user.id
    receiver_username = message.reply_to_message.from_user.username
    receiver_first_name = message.reply_to_message.from_user.first_name

    if sender_id == receiver_id:
        await message.reply_text("You can't gift a character to yourself!")
        return

    if len(message.command) != 2:
        await message.reply_text("You need to provide a character ID!")
        return

    character_id = message.command[1]

    sender = await user_collection.find_one({'id': sender_id})

    # Check if user exists and has characters field
    if not sender or not sender.get('characters'):
        await message.reply_text("You don't have any characters to gift!")
        return

    character = next((character for character in sender['characters'] if character['id'] == character_id), None)

    if not character:
        await message.reply_text("You don't have this character in your collection!")
        return

    
    pending_gifts[(sender_id, receiver_id)] = {
        'character': character,
        'receiver_username': receiver_username,
        'receiver_first_name': receiver_first_name
    }

    
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Confirm Gift", callback_data="confirm_gift")],
            [InlineKeyboardButton("Cancel Gift", callback_data="cancel_gift")]
        ]
    )

    await message.reply_text(f"Do you want to gift character ID `{character_id}` ({character['name']}) to {message.reply_to_message.from_user.mention}?", reply_markup=keyboard, parse_mode='Markdown')

@shivuu.on_callback_query(filters.create(lambda _, __, query: query.data in ["confirm_gift", "cancel_gift"]))
async def on_gift_callback_query(client, callback_query):
    sender_id = callback_query.from_user.id

    
    for (_sender_id, receiver_id), gift in pending_gifts.items():
        if _sender_id == sender_id:
            break
    else:
        await callback_query.answer("This is not for you!", show_alert=True)
        return

    if callback_query.data == "confirm_gift":
        
        sender = await user_collection.find_one({'id': sender_id})
        receiver = await user_collection.find_one({'id': receiver_id})

        # Check if sender still exists and has characters
        if not sender or not sender.get('characters'):
            await callback_query.answer("You no longer have characters to gift!", show_alert=True)
            return
        
        sender['characters'].remove(gift['character'])
        await user_collection.update_one({'id': sender_id}, {'$set': {'characters': sender['characters']}})

        
        if receiver:
            await user_collection.update_one({'id': receiver_id}, {'$push': {'characters': gift['character']}})
        else:
            
            await user_collection.insert_one({
                'id': receiver_id,
                'username': gift['receiver_username'],
                'first_name': gift['receiver_first_name'],
                'characters': [gift['character']],
            })

        
        del pending_gifts[(sender_id, receiver_id)]

        await callback_query.message.edit_text(f"You have successfully gifted your character to [{gift['receiver_first_name']}](tg://user?id={receiver_id})!")

    elif callback_query.data == "cancel_gift":
        
        del pending_gifts[(sender_id, receiver_id)]

        await callback_query.message.edit_text("❌️ Gift Cancelled....")


@shivuu.on_message(filters.command("give"))
async def give(client, message):
    """Admin-only command to give characters to users"""
    sender_id = message.from_user.id
    
    # Check if user is admin
    if str(sender_id) not in Config.sudo_users:
        await message.reply_text("🚫 This command is only available to administrators.")
        return
    
    # Command format: /give <character_id> <user_id>
    # Or: /give <character_id> (when replying to a user)
    
    if message.reply_to_message:
        # Giving to the user being replied to
        if len(message.command) != 2:
            await message.reply_text("📝 **Give Character**\n\nUsage when replying: `/give <character_id>`\nExample: `/give 1`")
            return
            
        character_id = message.command[1]
        receiver_id = message.reply_to_message.from_user.id
        receiver_username = message.reply_to_message.from_user.username
        receiver_first_name = message.reply_to_message.from_user.first_name
        
    else:
        # Giving to a specific user ID
        if len(message.command) != 3:
            await message.reply_text("📝 **Give Character**\n\nUsage: `/give <character_id> <user_id>`\nExample: `/give 1 123456789`\n\nOr reply to a user: `/give <character_id>`")
            return
            
        character_id = message.command[1]
        try:
            receiver_id = int(message.command[2])
        except ValueError:
            await message.reply_text("❌ Invalid user ID. Please provide a valid number.")
            return
            
        receiver_username = None
        receiver_first_name = "User"
    
    # Find the character in the database
    character = await collection.find_one({'id': character_id})
    if not character:
        await message.reply_text(f"❌ Character with ID `{character_id}` not found in the database.")
        return
    
    # Check if receiver exists in database, if not create entry
    receiver = await user_collection.find_one({'id': receiver_id})
    if receiver:
        # Add character to existing user
        await user_collection.update_one(
            {'id': receiver_id}, 
            {'$push': {'characters': character}}
        )
    else:
        # Create new user entry
        await user_collection.insert_one({
            'id': receiver_id,
            'username': receiver_username,
            'first_name': receiver_first_name,
            'characters': [character],
        })
    
    # Success message
    if message.reply_to_message:
        await message.reply_text(
            f"✅ **Character Given!**\n\n"
            f"🎴 **{character['name']}** ({character['rarity']})\n"
            f"📺 From: **{character['anime']}**\n"
            f"👤 Given to: {message.reply_to_message.from_user.mention}\n"
            f"🆔 Character ID: `{character['id']}`"
        )
    else:
        await message.reply_text(
            f"✅ **Character Given!**\n\n"
            f"🎴 **{character['name']}** ({character['rarity']})\n"
            f"📺 From: **{character['anime']}**\n"
            f"👤 Given to: User ID `{receiver_id}`\n"
            f"🆔 Character ID: `{character['id']}`"
        )


