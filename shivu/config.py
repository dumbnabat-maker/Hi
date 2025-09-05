import os

class Config(object):
    LOGGER = True

    # Get this value from my.telegram.org/apps
    OWNER_ID = os.environ.get("OWNER_ID", "6765826972")
    sudo_users = os.environ.get("SUDO_USERS", "6845325416,6765826972").split(",")
    GROUP_ID = int(os.environ.get("GROUP_ID", "-1002133191051"))
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    mongo_url = os.environ.get("MONGODB_URL")
    PHOTO_URL = ["https://drive.google.com/uc?id=18eGUijT2Egx7OyBYgNXVLBQ4bCnFJCnK&export=download"]
    SUPPORT_CHAT = os.environ.get("SUPPORT_CHAT", "Collect_em_support")
    UPDATE_CHAT = os.environ.get("UPDATE_CHAT", "Collect_em_support")
    BOT_USERNAME = os.environ.get("BOT_USERNAME", "Collect_Em_AllBot")
    CHARA_CHANNEL_ID = os.environ.get("CHARA_CHANNEL_ID", "-1002133191051")
    api_id = int(os.environ.get("TELEGRAM_API_ID", "0"))
    api_hash = os.environ.get("TELEGRAM_API_HASH")

    
class Production(Config):
    LOGGER = True


class Development(Config):
    LOGGER = True
