import discord
import asyncio
import time
import json
import os
import pyAesCrypt

from hashlib import md5
from databases import Database

query_reports_create = 'CREATE TABLE IF NOT EXISTS reports (id STRING PRIMARY KEY, ip STRING, ping INTEGER, start_time INTEGER, stop_time INTEGER, runes INTEGER)'
query_reports_add = 'INSERT into reports (ip, start_time, stop_time, runes) values("%s", %d, %d, %d)'
query_reports_all = 'SELECT * from reports';

query_create_table = 'CREATE TABLE IF NOT EXISTS active (id STRING PRIMARY KEY, ip STRING, ping INTEGER, start_time INTEGER, stop_time INTEGER, runes INTEGER)'
query_active_all = 'SELECT * FROM active'
query_select = 'SELECT * FROM active WHERE id = "%s"'
query_active_delete_id = 'DELETE FROM active WHERE id = "%s"'
query_active_add = 'INSERT into active (id, ip, ping, start_time, stop_time, runes) values("%s", "%s", %d, %d, %d, %d)'
query_active_update = 'UPDATE active SET ping=%d, runes=%d where id = "%s"'

class bot(discord.Client):

	async def on_ready(self):
		try:
			unix = int(time.time());
				
			database = Database('sqlite:///database')
			
			await database.connect()
			await database.execute(query_create_table)
			await database.execute(query_reports_create)	

			for channel in self.get_all_channels():
				if (channel.name == 'incoming'):
					messages = await channel.history(limit=None).flatten()
					for message in messages:
						data = json.loads(message.content)
						
						ip = data["ip"]
						runes = data["runes"]
						id = md5(str(data["ip"] + data["time"]).encode('utf-8')).hexdigest();
						
						row = await database.fetch_one(query_select % id) 
						if row == None:
							await database.execute(query_active_add % (id, ip, unix, unix, unix, runes))	
						else:
							await database.execute(query_active_update % (unix, runes + row.runes, id))	
						
					await channel.delete_messages(messages)
					
				if (channel.name == 'report'):
					lines = [];
					
					rows = await database.fetch_all(query_active_all)
					for row in rows:
						if (unix - row.ping > 10 * 60):
							await database.execute(query_reports_add % (row.ip, row.start_time, unix, row.runes))
							await database.execute(query_active_delete_id % (row.id))
						else:
							ip = row.ip
							seconds = unix - row.start_time
							timestamp = '{:02}:{:02}:{:02}'.format(seconds//3600, seconds%3600//60, seconds%60)
							runes = format(row.runes, ",d")
							
							lines.append(ip.ljust(20, " ") + timestamp.ljust(15, " ") + runes + " runes\n")
					
					lines.sort()
					
					report  = "```"
					report += "Online bots: %d" % len(lines)
					report += "\n\n"
					report += "".join(lines);
					report += "```"
					
					total = {}
					rows = await database.fetch_all(query_reports_all);
					for row in rows:
						total[row.ip] = total.get(row.ip, 0) + row.runes
					
					report += "```"
					report += "Total:" 
					report += "\n\n"
					for key in sorted(total):
						report += key.ljust(20, " ") + format(total[key], ",d") + " runes\n"
					
					report += "```"
					
					messages = await channel.history(limit=None).flatten()
					if len(messages) == 0:
						await channel.send(content=report)
					else:
						await messages[0].edit(content=report)
		
		except Exception as e:
			print("Exception: ", e)
							
		await self.logout()

if os.path.isfile("database.aes"):
    pyAesCrypt.decryptFile("database.aes", "database", os.environ['password'], 512 * 512)

bot().run(os.environ['token'])

if os.path.isfile("database"):
    pyAesCrypt.encryptFile("database", "database.aes", os.environ['password'], 512 * 512) # only IP addresses but encrpyt to keep people happy
