# cod4xscreenshot-b3-plugin

Plugin for BigBrotherBot to capture screenshot of players on CoD4x servers.
The screenshot is then uploaded to ImgBB and the generated link is sent to Discord server.

Requirements:
- ImgBB API Key - https://api.imgbb.com/
- Discord channel webhook - https://discordjs.guide/popular-topics/webhooks.html

Installation:
- Create a folder in your b3/extplugins directory and name it "cod4xscreenshot".
- Copy the "conf" folder and its contents into that directory.
- Copy "__init__.py" into that directory alongside the conf folder.
- Edit the conf/cod4xscreenshot.ini file and put in the required information.
- Enter the following line into the b3.ini file in the [plugins] sections

    cod4xscreenshot: @b3/extplugins/cod4xscreenshot/conf/cod4xscreenshot.ini
    
- Restart B3 and you're done.
