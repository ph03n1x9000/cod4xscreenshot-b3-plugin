# BigBrotherBot(B3) (www.bigbrotherbot.com)
#
# Plugin to capture screenshots of players on CoD4X servers and
# upload to Discord server.
#
# Copyright (C) 2021 Sh3llK0de
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

__version__ = '0.0.5'
__author__ = 'Sh3llK0de'


import b3.plugin
from b3.functions import getCmd
from base64 import b64encode
import requests
import json
import os
import time
from threading import Thread


class Cod4XscreenshotPlugin(b3.plugin.Plugin):
    requiresParsers = ['cod4', 'cod4x18']
    adminPlugin = None
    screenshotpath = None
    imgbb_api = None
    discordwebhook = None
    screenshotting = []  # Stores list of players that is currently being screenshotted.
    serverinfo = 'CoD4 Server'
    expiration = 0
    

    # -------------------- PLUGIN STARTUP --------------------------
    def onStartup(self):
        """
        Initiate plugin
        """
        self.adminPlugin = self.console.getPlugin('admin')
        if not self.adminPlugin:
            # something is wrong, can't start without admin plugin
            self.error('Could not find admin plugin')
            self.disable()
            return False
        # Register commands
        self.registercommands()
        
    def registercommands(self):
        """
        Registers commands using the admin plugin
        """
        if 'commands' in self.config.sections():
            for cmd in self.config.options('commands'):
                level = self.config.get('commands', cmd)
                sp = cmd.split('-')
                alias = None
                if len(sp) == 2:
                    # this will split the command name and the alias
                    cmd, alias = sp
                # retrieve the method implementing the command
                func = getCmd(self, cmd)
                if func:
                    # register the command is a valid method is found
                    self.adminPlugin.registerCommand(self, cmd, level, func, alias)

    def onLoadConfig(self):
        """
        Loads data from the configuration file.
        """
        try:
            savepath = self.console.getCvar('fs_savepath').value
            self.screenshotpath = savepath + '/screenshots/'
            self.verbose('Screenshot path: %s' % self.screenshotpath)
        except Exception as error:
            self.error(error)
            self.debug("Could not retrieve fs_savepath from server. PLUGIN DISABLED.")
            self.disable()

        try:
            self.imgbb_api = self.config.get('settings', 'imgbb_apikey')
            self.verbose('Successfully loaded settings::imgbb_apikey from config.')
        except Exception as error:
            self.error(error)
            self.error('Error loading settings::imgbb_apikey. PLUGIN DISABLED.')
            self.disable()

        try:
            self.discordwebhook = self.config.get('settings', 'discord_webhook')
            self.verbose('Successfully loaded settings::discord_webhook from config.')
        except Exception as error:
            self.error('Could not load settings::discord_webhook from config %s. PLUGIN DISABLED.' % error)
            self.disable()

        try:
            self.serverinfo = self.console.stripColors(self.console.getCvar('sv_hostname').value)
            self.verbose('sv_hostname captured as server name: %s' % self.serverinfo)
        except Exception as err:
            self.error(err)

        try:
            self.expiration = int(self.config.get('settings', 'link_expire'))
            if self.expiration < 60 and self.expiration > 0:
                self.expiration = 0
            if self.expiration > 15552000:
                self.expiration = 15552000
            self.verbose('Successfully loaded settings::link_expire => %s' % self.expiration)
        except Exception:
            self.verbose('Error loading settings::link_expire. Using %s' % self.expiration)

    # ------------------- SCREENSHOT HANDLING -------------------------
    def processloop(self, client, admin):
        """
        Uses a threaded loop to process screenshot.
        :client: The client whose screenshot was taken.
        """
        self.debug('Getting screenshot of %s' % client.name)
        # Use partial GUID and a timestring as name of file. Ensures no illegal chars are used.
        screenshot_name = str(client.guid)[9:] + "_" + str(int(time.time()))
        # The name will be unique due to unix timestamp in file name, so we know what the file will be named.
        screenshot_name_full = self.screenshotpath + screenshot_name + '0000.jpg'
        # Send command to server to take screenshot.
        self.console.write('getss %s %s' % (client.cid, screenshot_name))
        self.screenshotting.append(client)
        time.sleep(5)

        tries, failed = (0, True)
        wait_interval = 2
        while tries < 60:
            tries += 1
            time.sleep(2)
            self.verbose('File exists check: Try %s/60 for screenshot of %s' % (tries, client.name))
            if os.path.exists(screenshot_name_full):
                failed = False
                break

        self.screenshotting.remove(client)
        # Check if we found the file.
        if failed:
            self.error('Too many attempts to process screenshot for %s. Cancelled' % client.name)
            admin.message('Error encountered when capturing screenshot of %s.' % client.name)
            return
      
        # Upload file to ImgBB and get share link.
        link = self.imgbb_upload(screenshot_name_full)
        if link is None or 'data' not in link or 'url' not in link['data']:
            self.error('Received null response from ImgBB: player: %s filename: %s' % (client.name, screenshot_name))
            admin.message('Failed to upload image to hosting service.')
            return

        link = link['data']['url']
        # Call function to send link to Discord server and give it the link.
        sent = self.discordsend(link, client, admin)
        if not sent:
            admin.message('Error uploading screenshot of %s to Discord' % client.name)
            return

        self.verbose('Processed screenshot for %s successfully. Sending to Discord.' % client.name)
        admin.message('^2Screenshot if %s ^2ready for viewing.' % client.name)
        

    def imgbb_upload(self, image):
        """
        Uploads image to imgbb database.
        :image: The name of the image to be uploaded
        """
        if not image:
            self.error('No image entered. Cancelled.')
            return
        with open(image, 'rb') as filetoupload:
            payload = {'key': self.imgbb_api, 'image': b64encode(filetoupload.read())}
            if self.expiration:
                payload['expiration'] = self.expiration
            response = requests.post('https://api.imgbb.com/1/upload', payload)
        link = response.json()
        filetoupload.close()
        return link

    def discordsend(self, imageURL, client, admin):
        """
        Send the provided imageURL to discord.
        """
        content = 'Screenshot of %s from %s. - Taken by %s' % (client.name, self.serverinfo, admin.name)
        data = json.dumps({"content": content, "username": "B3 Screenshot",
                           "embeds": [{"image": {"url": imageURL}}]})

        result = requests.post(self.discordwebhook, data=data, headers={'Content-Type': 'application/json'})

        try:
            result.raise_for_status()
        except requests.exceptions.HTTPError as err:
            self.error(err)
            return False
        else:
            self.verbose("Sent message successfully, code: %s." % result.status_code)
            return True

    # ------------------------- COMMANDS -------------------------------
    def cmd_screenshot(self, data, client, cmd=None):
        """\
        <player> Capture a snapshot of a player's screen.
        """
        if not data:
            client.message('Invalid usage. Use !help screenshot for info')
            return
        sclient = self.adminPlugin.findClientPrompt(data, client)
        if not sclient:
            return
        if sclient.bot:
            client.message('Player is a bot. Screenshot will NOT be taken.')
            return
        if sclient in self.screenshotting:
            client.message('%s already has a screenshot in processing. Stand by.')
            return
        t = Thread(target=self.processloop, args=(sclient, client))
        t.start()
        client.message('^2Taking screenshot of %s ^2. Stand by...' % sclient.name)