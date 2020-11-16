from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import logging
import json
import requests
import db

from bitcoinutils.setup import setup
from bitcoinutils.keys import P2wpkhAddress, P2wshAddress, P2shAddress, P2pkhAddress, PrivateKey
from bitcoinutils.transactions import Transaction, TxInput, TxOutput
from bitcoinutils.script import Script

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

config = {}
with open("configs/config.json", "r") as f:
    config = (json.load(f))

### COMMANDS

def help(update, ctx):
    user = update.message.from_user
    if user["username"]:
        if not db.checkUser(str(user["id"])):
            wif = genAddress()
            db.addUser(str(user["username"]), str(user["id"]), str(wif))
            ctx.bot.send_message(chat_id=update.message.chat_id, text=f"[{user['first_name']}](tg://user?id={user['id']}), You have been successfully registered", parse_mode="MarkdownV2")
            ctx.bot.send_message(chat_id=update.message.chat_id, text=f"""
    Hey there [{user['first_name']}](tg://user?id={user['id']})\\. Here are my commands:
    1\\. /help
    2\\. /price
    3\\. /tip @user amount
    4\\. /deposit
    5\\. /balance
    6\\. /withdraw address amount
            """, parse_mode="MarkdownV2")
            ctx.bot.send_message(chat_id=update.message.chat_id,
                                 text="*Please Note: * It is highly recommended that you do not directly mine to the "
                                      "address given by this bot\\. Download a full node here: "
                                      "[Full Node](https://github\\.com/sugarchain\\-project/sugarchain/releases/latest)",
                                 parse_mode="MarkdownV2")
        else:
            ctx.bot.send_message(chat_id=update.message.chat_id, text=f"""
    Hey there [{user['first_name']}](tg://user?id={user['id']})\\. Here are my commands:
    1\\. /help
    2\\. /price
    3\\. /tip @user amount
    4\\. /deposit
    5\\. /balance
    6\\. /withdraw address amount
            """, parse_mode="MarkdownV2")
            ctx.bot.send_message(chat_id=update.message.chat_id,
                                 text="*Please Note: * It is highly recommended that you do not directly mine to the "
                                      "address given by this bot\\. Download a full node here: "
                                      "[Full Node](https://github\\.com/sugarchain\\-project/sugarchain/releases/latest)",
                                 parse_mode="MarkdownV2")
    else:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"[{user['first_name']}](tg://user?id={user['id']}), please set a username before using this bot", parse_mode="MarkdownV2")

def price(update, ctx):

    price = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={config['coin']['coin_name']}&vs_currencies=usd,btc").json()

    btc = str(format(price["sugarchain"]["btc"], '.8f'))
    usd = str(price["sugarchain"]["usd"])

    ctx.bot.send_message(chat_id=update.message.chat_id, text=f"Current {config['coin']['ticker']}/BTC price: {btc} BTC\nCurrent {config['coin']['ticker']}/USD price: ${usd}")

def tip(update, ctx):
    user = update.message.from_user
    args = update.message.text.split(" ")

    if not db.checkUser(user["id"]):
        ctx.bot.send_message(chat_id=update.message.chat_id,
                             text="It looks like you haven't registered yet. Please run /help first to register yourself")
    else:
        target = None
        try:
            target = args[1][1:]
        except IndexError:
            target = target

        amount = None
        try:
            amount = args[2]
        except IndexError:
            amount = amount

        if target is not None:
            if not db.getUserID(target):
                ctx.bot.send_message(chat_id=update.message.chat_id,
                                     text="Oops, looks like your sending to a user who hasn't registered. Ask them to do /help to register!\nPlease be mindful that usernames are case senstive. Make sure that the case of the target is correct.")
            else:
                if user["username"] == target:
                    ctx.bot.send_message(chat_id=update.message.chat_id, text="😆 You can't tip yourself!")
                else:
                    if amount is not None:
                        if isFloat(amount):
                            if float(amount) > float(config['coin']['minFee']):
                                keyboard = [
                                    [
                                        InlineKeyboardButton("Yes", callback_data=f"Y, {target}, {amount}, {user['id']}, tip"),
                                        InlineKeyboardButton("No", callback_data=f"N, {target}, {amount}, {user['id']}, tip")
                                    ]
                                ]
                                reply_markup = InlineKeyboardMarkup(keyboard)
                                ctx.bot.send_message(chat_id=update.message.chat_id,
                                                     text=f"You are about to send {amount} {config['coin']['ticker']} with an additional fee of {format(config['coin']['minFee'], '.8f')} SUGAR to @{target}. Please click Yes to confirm",
                                                     reply_markup=reply_markup)
                            else:
                                ctx.bot.send_message(chat_id=update.message.chat_id,
                                                     text="You cannot send negative amounts or amounts less than 0.00001!")
                        else:
                            ctx.bot.send_message(chat_id=update.message.chat_id,
                                                 text="Invalid amount of SUGAR. Please try again")
                    else:
                        ctx.bot.send_message(chat_id=update.message.chat_id, text="No amount specified!")
        else:
            ctx.bot.send_message(chat_id=update.message.chat_id, text="No user specified!")


def withdraw(update, ctx):
    user = update.message.from_user
    args = update.message.text.split(" ")

    if not db.checkUser(user['id']):
        ctx.bot.send_message(chat_id=update.message.chat_id,
                             text="It looks like you haven't registered yet. Please run /help first to register yourself")
    else:
        address = None
        try:
            address = str(args[1])[7:]
        except IndexError:
            address = address

        amount = None
        try:
            amount = args[2]
        except IndexError:
            amount = amount

        if address is not None:
            if checkAdd("sugar1q" + address):
                if amount is not None:
                    if isFloat(amount):
                        if float(amount) > float(config['coin']['minFee']):
                            keyboard = [
                                [
                                    InlineKeyboardButton("Yes", callback_data=f"Y, {address}, {amount}, {user['id']}, w"),
                                    InlineKeyboardButton("No", callback_data=f"N, {address}, {amount}, {user['id']}, w")
                                ]
                            ]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            ctx.bot.send_message(chat_id=update.message.chat_id,
                                                 text=f"You are about to withdraw {amount} {config['coin']['ticker']}, with a fee of {format(config['coin']['minFee'], '.8f')} SUGAR to {'sugar1q' + address}. Please click Yes to confirm",
                                                 reply_markup=reply_markup)
                        else:
                            ctx.bot.send_message(chat_id=update.message.chat_id, text="You cannot withdraw negative amounts or amounts less than 0.00001")
                    else:
                        ctx.bot.send_message(chat_id=update.message.chat_id, text="The amount you have specified is not valid. Please try again.")
                else:
                    ctx.bot.send_message(chat_id=update.message.chat_id, text="You did not specify the amount you wish to withdraw. Please try again")
            else:
                ctx.bot.send_message(chat_id=update.message.chat_id, text="You have specified an invalid withdraw address. Try again with a valid address.")
        else:
            ctx.bot.send_message(chat_id=update.message.chat_id, text="No withdraw address specified")





def deposit(update, ctx):
    user = update.message.from_user

    if not db.checkUser(user["id"]):
        ctx.bot.send_message(chat_id=update.message.chat_id, text="It looks like you haven't registered yet. Please run /help first to register yourself")
    else:

        address = getAddress(user["id"])

        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"Your deposit address: {address}")

def balance(update, ctx):
    user = update.message.from_user

    if not db.checkUser(user["id"]):
        ctx.bot.send_message(chat_id=update.message.chat_id, text="It looks like you haven't registered yet. Please run /help first to register yourself")
    else:
        balance = getBalance(user["id"])

        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"You current balance: {balance} {config['coin']['ticker']}")

### FUNCTIONS

def isFloat(amount):
    try:
        float(amount)
        return True
    except ValueError:
        return False


def genAddress():
    # Initialise bitcoin.py
    setup('mainnet')

    priv = PrivateKey()
    wif = priv.to_wif(compressed=True)

    return wif


def tip_or_withdrawFunc(update, ctx):
    # Initialise bitcoin.py
    setup('mainnet')
    query = update.callback_query
    chID = query.message.chat.id
    msgID = query.message.message_id
    query.answer()
    data = str(query.data).split(", ")
    sender = str(query.from_user.id)
    if sender == data[3]:
        if data[4] == "tip":
            target = db.getUserID(data[1])
            if data[0] == "Y":
                ctx.bot.delete_message(chat_id=chID, message_id=msgID)

                sender_wif = PrivateKey(db.getWIF(sender))
                fee = convertToSatoshis(float(config['coin']['minFee']))
                target_address = P2wpkhAddress(getAddress(target))
                sender_address = P2wpkhAddress(getAddress(sender))
                sender_balance = 0
                amount = convertToSatoshis(float(data[2])) + fee

                unspent = requests.get(f"{config['apiUrl']}/unspent/{sender_address.to_string()}").json()["result"]
                txin = []
                for i in range(0, len(unspent)):
                    sender_balance += unspent[i]['value']
                    txin.append(TxInput(unspent[i]['txid'], unspent[i]['index']))

                if sender_balance >= amount:

                    txout = []
                    txout.append(TxOutput((amount - fee), target_address.to_script_pub_key()))

                    txchange = sender_balance - amount
                    if txchange > 0:
                        txout.append(TxOutput(txchange, sender_address.to_script_pub_key()))

                    script_code = Script(['OP_DUP', 'OP_HASH160', sender_wif.get_public_key().to_hash160(), 'OP_EQUALVERIFY', 'OP_CHECKSIG'])

                    tx = Transaction(txin, txout, has_segwit=True)

                    tx.witnesses = []

                    for i in range(0, len(unspent)):
                        value = unspent[i]['value']
                        sig = sender_wif.sign_segwit_input(tx, i, script_code, value)
                        tx.witnesses.append(Script([sig, sender_wif.get_public_key().to_hex()]))

                    post_data = {
                        'raw': tx.serialize()
                    }

                    txid = requests.post(f"{config['apiUrl']}/broadcast", data=post_data).json()['result']

                    ctx.bot.send_message(chat_id=chID, text=f"Success, sent @{data[1]} {data[2]} {config['coin']['ticker']}.")
                    ctx.bot.send_message(chat_id=chID, text=f"[View Transaction](https://sugar\\.wtf/esplora/tx/{str(txid)})", parse_mode="MarkdownV2")
                else:
                    ctx.bot.send_message(chat_id=chID, text="You do not have enough funds to tip that amount")

            elif data[0] == "N":
                ctx.bot.delete_message(chat_id=chID, message_id=msgID)
                ctx.bot.send_message(chat_id=chID, text=f"You declined sending @{data[1]} {data[2]} {config['coin']['ticker']}")

        elif data[4] == "w":
            if data[0] == "Y":
                ctx.bot.delete_message(chat_id=chID, message_id=msgID)

                sender_wif = PrivateKey(db.getWIF(sender))
                fee = convertToSatoshis(float(config['coin']['minFee']))
                sender_address = P2wpkhAddress(getAddress(sender))
                sender_balance = 0
                amount = convertToSatoshis(float(data[2])) + fee
                target_address = P2wpkhAddress("sugar1q" + data[1])

                unspent = requests.get(f"{config['apiUrl']}/unspent/{sender_address.to_string()}").json()['result']

                txin = []
                for i in range(0, len(unspent)):
                    sender_balance += unspent[i]['value']
                    txin.append(TxInput(unspent[i]['txid'], unspent[i]['index']))

                if sender_balance >= amount:
                    txout = []
                    
                    txout.append(TxOutput((amount - fee), target_address.to_script_pub_key()))

                    txchange = sender_balance - amount
                    if txchange > 0:
                        txout.append(TxOutput(txchange, sender_address.to_script_pub_key()))

                    script_code = Script(['OP_DUP', 'OP_HASH160', sender_wif.get_public_key().to_hash160(), 'OP_EQUALVERIFY', 'OP_CHECKSIG'])

                    tx = Transaction(txin, txout, has_segwit=True)

                    tx.witnesses = []

                    for i in range(0, len(unspent)):
                        value = unspent[i]['value']
                        sig = sender_wif.sign_segwit_input(tx, i, script_code, value)
                        tx.witnesses.append(Script([sig, sender_wif.get_public_key().to_hex()]))

                    post_data = {
                        'raw': tx.serialize()
                    }

                    txid = requests.post(f"{config['apiUrl']}/broadcast", data=post_data).json()['result']

                    ctx.bot.send_message(chat_id=chID, text=f"Success, withdrew {data[2]} {config['coin']['ticker']} to address {target_address.to_string()} ")
                    ctx.bot.send_message(chat_id=chID, text=f"[View Transaction](https://sugar\\.wtf/esplora/tx/{str(txid)})", parse_mode="MarkdownV2")
                else:
                    ctx.bot.send_message(chat_id=chID, text="You do not have enough funds to withdraw the specified amount.")
            elif data[0] == "N":
                ctx.bot.delete_message(chat_id=chID, message_id=msgID)
                ctx.bot.send_message(chat_id=chID, text=f"You declined withdrawing {data[2]} {config['coin']['ticker']} to address {data[1]}")


def getBalance(id: str):

    address = getAddress(id)

    getBalance = requests.get(f"{config['apiUrl']}/balance/{address}").json()["result"]["balance"]
    userBalance = getBalance / 100000000

    return userBalance


def checkAdd(address: str):
    check = requests.get(f"{config['apiUrl']}/balance/{address}").json()

    if check['error']:
        return False
    else:
        return True


def getAddress(id: str):
    # Initialise bitcoin.py
    setup('mainnet')
    wif = db.getWIF(id)

    priv = PrivateKey.from_wif(f"{wif}")

    pub = priv.get_public_key()

    address = pub.get_segwit_address().to_string()

    return address

def convertToSatoshis(amount: float):
    return int(round(amount * 100000000))

def convertToSugar(amount: int):
    return float(round(amount / 100000000))

### LAUNCH

def main():

    updater = Updater(token=config["token"], use_context=True, workers=10)

    dispatcher = updater.dispatcher

    help_command = CommandHandler('help', help)
    price_command = CommandHandler('price', price)
    tip_command = CommandHandler('tip', tip)
    deposit_command = CommandHandler('deposit', deposit)
    balance_command = CommandHandler('balance', balance)
    withdraw_command = CommandHandler('withdraw', withdraw)
    tip_or_withdraw_handler = CallbackQueryHandler(tip_or_withdrawFunc)
    dispatcher.add_handler(help_command)
    dispatcher.add_handler(price_command)
    dispatcher.add_handler(tip_command)
    dispatcher.add_handler(deposit_command)
    dispatcher.add_handler(balance_command)
    dispatcher.add_handler(withdraw_command)

    dispatcher.add_handler(tip_or_withdraw_handler)

    updater.start_polling()
    updater.idle()
    updater.stop()


if __name__ == '__main__':
    main()


