import re
import time
import requests
import json
import sqlite3
import os
import configparser

from datetime import datetime, timedelta, timezone


# read config
config = configparser.ConfigParser()
config.read("config.ini")
file_path_log = config["GAME"]["Log"]
file_path_db = config["GAME"]["Database"]
webhook = config["DISCORD"]["Webhookurl"]
webhook_name = config["DISCORD"]["Webhookname"]
timezone = int(config["TIME"]["Timezone"])

# check files if exist
if not os.path.exists(file_path_log):
    print("Please check your config, ConanSandbox.log not found")
    input("Press the <ENTER> key to continue...")
    exit()
if not os.path.exists(file_path_db):
    print("Please check your config, game.db or DLC_Siptah.db not found")
    input("Press the <ENTER> key to continue...")
    exit()

# check log filesize (for detect new logfile)
file_size_log = os.stat(file_path_log).st_size

# read logfile
def read_log(logfile):
    global file_size_log
    logfile.seek(0, 2)
    while True:
        line = logfile.readline()
        if len(line) < 2:
            if file_size_log > os.stat(file_path_log).st_size:
                print(os.stat(file_path_log).st_size)
                exit()
            file_size_log = os.stat(file_path_log).st_size
            time.sleep(0.1)
            continue
        else:
            yield line

# send discord webhook
def discord_webook(message):
    try:
        data = {}
        data["content"] = message
        data["username"] = webhook_name
        result = requests.post(webhook, data=json.dumps(data), headers={"Content-Type": "application/json"})
        result.raise_for_status()
    except Exception:
        print("an error occurred while sending the discord message")
        pass

def save_log(loglist):
    try:
        # open db connection
        connection = sqlite3.connect(os.getcwd()+"\serverlog.db")
        cursor = connection.cursor()

        if loglist[0] == "chat":
            cursor.execute(f"INSERT INTO chat (name, text, time) VALUES ('{loglist[1]}', '{loglist[2]}', '{loglist[3]}')")
            connection.commit()

        if loglist[0] == "connection":
            cursor.execute(f"INSERT INTO connection (type, name, steamid, ip, time) VALUES ('{loglist[1]}', '{loglist[2]}', '{loglist[3]}', '{loglist[4]}', '{loglist[5]}')")
            connection.commit()

        if loglist[0] == "error":
            cursor.execute(f"INSERT INTO error (message, time) VALUES ('{loglist[1]}', '{loglist[2]}')")
            connection.commit()

        if loglist[0] == "newplayer":
            cursor.execute(f"INSERT INTO newplayer (name, time) VALUES ('{loglist[1]}', '{loglist[2]}')")
            connection.commit()

        if loglist[0] == "purge":
            cursor.execute(f"INSERT INTO purge (status, name, type, x, y, time) VALUES ('{loglist[1]}', '{loglist[2]}', '{loglist[3]}', '{loglist[4]}', '{loglist[5]}', '{loglist[6]}')")
            connection.commit()

        if loglist[0] == "serverload":
            cursor.execute(f"INSERT INTO serverload (type, time) VALUES ('{loglist[1]}', '{loglist[2]}')")
            connection.commit()

        # close db connection
        cursor.close()
        connection.close()

    except sqlite3.Error:
        print("an error occurred while opening/write the logdatabase")
        pass

# convert time
def convert_time(time):
    time = datetime.strptime(time, "%Y.%m.%d-%H.%M.%S:%f") + timedelta(hours=timezone)
    time = time.strftime("%Y-%m-%d %H:%M:%S")
    return time


if __name__ == "__main__":
    temp_player = ""

    # open logfile
    try:
        logfile = open(file_path_log, "r", encoding="utf-8", errors="ignore")
    except OSError as err:
        print(f"an error occurred while opening the logfile ({err})")
        exit()

    # read logfile line
    for line in read_log(logfile):

        # detect Chatmessages
        if "ChatWindow" in line:
            log_time = re.findall("\[(.*?)\]", line)
            log_character = re.findall("(?<=Character )(.*)(?= said)", line)
            log_text = re.findall("(?<=said: )(.*)", line)

            # convert datetime
            log_time = convert_time(log_time[0])

            # send webhook to discord
            discord_webook(f"{log_time} :speech_balloon: {log_character[0]}: {log_text[0]}")

            # save to sqlite database
            save_log(["chat", log_character[0], log_text[0], log_time])

            print(f"Chat: {log_character[0]} ({log_text[0]})")

        # detect Error
        if "Error: Unhandled Exception:" in line:
            log_time = re.findall("\[(.*?)\]", line)
            log_error = re.findall("(?<=Unhandled Exception: )(.*)", line)

            # convert datetime
            log_time = convert_time(log_time[0])

            # send webhook to discord
            discord_webook(f"{log_time} :warning: {log_error[0]}")

            # save to sqlite database
            save_log(["error", log_error[0], log_time])

            print(f"Error: {log_error[0]}")

        # detect Shutdown
        if "LogExit: Game engine shut down" in line:
            log_time = re.findall("\[(.*?)\]", line)

            # convert datetime
            log_time = convert_time(log_time[0])

            # send webhook to discord
            discord_webook(f"{log_time} :o2: Engine shutdown")

            # save to sqlite database
            save_log(["serverload", "Engine shutdown", log_time])

            print(f"Engine shutdown")

        # detect Serverloaded
        if "LogLoad: (Engine Initialization)" in line:
            log_time = re.findall("\[(.*?)\]", line)

            # convert datetime
            log_time = convert_time(log_time[0])

            # send webhook to discord
            discord_webook(f"{log_time} :white_check_mark: Engine loaded")

            # save to sqlite database
            save_log(["serverload", "Engine loaded", log_time])

            print(f"Engine loaded")

        # detect New Player
        if "Join succeeded:" in line:
            log_time = re.findall("\[(.*?)\]", line)
            temp_player = re.findall("(?<=Join succeeded: )(.*)", line)

        if "Telling client to start Character Creation." in line:
            log_time = re.findall("\[(.*?)\]", line)
            log_character = temp_player

            # convert datetime
            log_time = convert_time(log_time[0])

            # send webhook to discord
            discord_webook(f"{log_time} :new: {log_character[0]}")

            # save to sqlite database
            save_log(["newplayer", log_character[0], log_time])

            print(f"New: {log_character[0]}")

        # detect IP
        if "BattlEyeServer: Print Message: Player " in line:
            log_ip = re.findall("(?<= \()(.*)(?=\:)", line)

        # detect Connect
        if "BattlEyeLogging: BattlEyeServer: Registering player" in line:
            log_time = re.findall("\[(.*?)\]", line)
            log_steamid = re.findall("(?<=BattlEyePlayerGuid )(.*)(?= and)", line)
            log_character = re.findall("(?<=name \')(.*)(?=\')", line)

            if not len(log_character) == 0:
                # convert datetime
                log_time = convert_time(log_time[0])

                # send webhook to discord
                discord_webook(f"{log_time} :green_square: {log_character[0]} (SteamID: {log_steamid[0]} | IP: {log_ip[0]})")

                # save to sqlite database
                save_log(["connection", "connect", log_character[0], log_steamid[0], log_ip[0], log_time])

                print(f"Connect: {log_character[0]} ({log_steamid[0]} | {log_ip[0]})")

        # detect Disconnect
        if " disconnected" in line:
            log_time = re.findall("\[(.*?)\]", line)
            log_character = re.findall("(?<=Player #[0-9] )(.*)(?= disconnected)", line)

            if len(log_character) == 0:
                log_character = re.findall("(?<=Player #[0-9][0-9] )(.*)(?= disconnected)", line)
            if len(log_character) == 0:
                log_character = re.findall("(?<=Player #[0-9][0-9][0-9] )(.*)(?= disconnected)", line)
            if not len(log_character) == 0:

                # convert datetime
                log_time = convert_time(log_time[0])

                # send webhook to discord
                discord_webook(f"{log_time} :red_square: {log_character[0]}")

                # save to sqlite database
                save_log(["connection", "disconnect", log_character[0], "", "", log_time])

                print(f"Disconnect: {log_character[0]}")

        # detect Purge Started
        if "Purge Started" in line:
            log_time = re.findall("\[(.*?)\]", line)
            log_clanid = re.findall("(?<=for Clan )(.*)(?=,)", line)
            log_x = re.findall("(?<=X=)(.*)(?=, Y)", line)
            log_y = re.findall("(?<=, Y=)(.*)(?=, Z)", line)
            log_wave = re.findall("(?<=Using Wave )(.*)", line)

            # convert datetime
            log_time = convert_time(log_time[0])

            try:
                # open db connection
                connection = sqlite3.connect(file_path_db)
                cursor = connection.cursor()

                # search clan or player
                cursor.execute(f"SELECT name FROM guilds WHERE guildId ={log_clanid[0]}")
                result_clan = cursor.fetchone()
                cursor.execute(f"SELECT char_name FROM characters WHERE id ={log_clanid[0]}")
                result_player = cursor.fetchone()

                if not result_clan == None:
                    log_name = result_clan[0]
                if not result_player == None:
                    log_name = result_player[0]

                # close db connection
                cursor.close()
                connection.close()

            except sqlite3.Error:
                print("an error occurred while opening the serverdatabase")
                log_name = "Unknown"
                pass

            # send webhook to discord
            discord_webook(f"{log_time} :crossed_swords: {log_name}, {log_wave[0]} (X: {log_x[0]} | Y: {log_y[0]})")

            # save to sqlite database
            save_log(["purge", "started", log_name, log_wave[0], log_x[0], log_y[0], log_time])

            print(f"Purge Started: {log_name} - {log_wave[0]} (X: {log_x[0]} | Y: {log_y[0]})")

        # detect Purge Failed
        if "Purge Failed" in line:
            log_time = re.findall("\[(.*?)\]", line)
            log_clanid = re.findall("(?<=for Clan )(.*)(?=, At)", line)
            log_reason = re.findall("(?<=, Reason )(.*)", line)

            # convert datetime
            log_time = convert_time(log_time[0])

            try:
                # open db connection
                connection = sqlite3.connect(file_path_db)
                sqlite3_cursor = connection.cursor()

                # search clan or player
                sqlite3_cursor.execute(f"SELECT name FROM guilds WHERE guildId ={log_clanid[0]}")
                result_clan = sqlite3_cursor.fetchone()
                sqlite3_cursor.execute(f"SELECT char_name FROM characters WHERE id ={log_clanid[0]}")
                result_player = sqlite3_cursor.fetchone()

                if not result_clan == None:
                    log_name = result_clan[0]
                if not result_player == None:
                    log_name = result_player[0]

                # close db connection
                cursor.close()
                connection.close()

            except sqlite3.Error:
                print("an error occurred while opening the serverdatabase")
                log_name = "Unknown"
                pass

            # send webhook to discord
            discord_webook(f"{log_time} :crossed_swords: {log_name} ({log_reason[0]})")

            # save to sqlite database
            save_log(["purge", "failed", log_name, log_reason[0], "", "", log_time])

            print(f"Purge Failed: {log_name} ({log_reason[0]})")