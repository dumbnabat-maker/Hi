characters = [
    {"name": "Hero A", "rarity": "Common", "image_url": "images/hero_a.png"},
    {"name": "Hero B", "rarity": "Rare", "image_url": "images/hero_b.png"},
    {"name": "Legend X", "rarity": "Legendary", "image_url": "images/legend_x.png"}
]
import random

def summon(update, context):
    char = random.choice(characters)  # randomly pick a character
    update.message.reply_text(f"You summoned {char['name']} ({char['rarity']})!")
    update.message.reply_photo(open(char['image_url'], "rb"))