import os
import asyncio
import logging
from typing import List

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from web3 import Web3
from dotenv import load_dotenv

# Load settings from .env file
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8614195963:AAGVIVKz4eR_7kbiBlH3GfV8VcVCNruUV7k")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "6150541410")

# Список отслеживаемых адресов
MONITORED_ADDRESSES_RAW = os.getenv(
    "MONITORED_ADDRESSES",
    "0x13CDee29cAd8e11523095900e2195088Ed6d02Ad,"
    "0x00cd5Bf5bFB8fd1d139eF486ce35B8dfc00aDE91,"
    "0x1f1C8b291B1C9cce6e7C1bee8F660f811Dcd5B94,"
    "0x8793291670607dDF746A49B6B3faf6627A5E494f"
)
MONITORED_ADDRESSES = {addr.strip().lower() for addr in MONITORED_ADDRESSES_RAW.split(",") if addr.strip()}

ETC_RPC_URL = os.getenv("ETC_RPC_URL", "https://etc.rivet.link")
THRESHOLD_ETC = float(os.getenv("THRESHOLD_ETC", 5000.0))

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(ETC_RPC_URL))

# Initialize Bot and Dispatcher
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


async def send_notification(tx_hash, from_addr, to_addr, value):
    """Send formatted HTML notification to Telegram."""
    message = (
        f"🚨 <b>Крупная транзакция в ETC!</b> 🚨\n\n"
        f"💳 <b>От:</b> <code>{from_addr}</code>\n"
        f"📥 <b>Кому:</b> <code>{to_addr}</code>\n"
        f"💰 <b>Сумма:</b> {value:.2f} ETC\n"
        f"🔗 <a href=\"https://etc.blockscout.com/tx/{tx_hash}\">Посмотреть в Blockscout</a>"
    )

    try:
        if ADMIN_CHAT_ID:
            await bot.send_message(ADMIN_CHAT_ID, message, parse_mode="HTML")
        else:
            logger.warning("ADMIN_CHAT_ID not set, skipping notification.")
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")


async def monitor_blocks():
    """Monitor ETC blockchain for large transactions."""
    if not w3.is_connected():
        logger.error("Failed to connect to ETC RPC.")
        return

    logger.info("Starting ETC block monitor...")
    last_block = w3.eth.block_number

    while True:
        try:
            current_block = w3.eth.block_number

            if current_block > last_block:
                for block_num in range(last_block + 1, current_block + 1):
                    logger.info(f"Processing block: {block_num}")
                    block = w3.eth.get_block(block_num, full_transactions=True)

                    for tx in block.transactions:
                        from_addr = tx["from"].lower()
                        to_addr = tx["to"].lower() if tx["to"] else ""
                        value_etc = w3.from_wei(tx["value"], "ether")

                        is_target = (
                            from_addr in MONITORED_ADDRESSES or
                            to_addr in MONITORED_ADDRESSES
                        )

                        if is_target and value_etc >= THRESHOLD_ETC:
                            logger.info(f"🔔 Транзакция: {tx['hash'].hex()} | {value_etc} ETC")
                            await send_notification(tx["hash"].hex(), from_addr, to_addr, value_etc)

                last_block = current_block

            await asyncio.sleep(10)

        except Exception as e:
            logger.error(f"Error in monitor loop: {e}")
            await asyncio.sleep(5)


@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Бот мониторинга ETC запущен и работает!")


async def main():
    asyncio.create_task(monitor_blocks())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
