# -*- coding: utf-8 -*-
# Copyright (c) 2010 by Jani Kesänen <jani.kesanen@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#
# Yahoo Weather to bar item
# (This script requires WeeChat 0.3.0.)
#
# Usage: Add "yweather" to weechat.bar.status.items or other bar you like.
#        Specify city: "/set plugins.var.python.yweather.city Tokyo".
#
#        Formatting: "/set plugins.var.python.yweather.format %C: %D°%U, %O".
#            Where: %C - city
#                   %D - temperature degrees
#                   %O - current condition
#
# History:
# 2012-12-6, Keith Johnson <kj@ubergeek42.com>:
#    version 0.4: replace google weather(no deprecated) with yahoo weather
# 2011-03-11, Sebastien Helleu <flashcode@flashtux.org>:
#   version 0.4: get python 2.x binary for hook_process (fix problem when
#                python 3.x is default python version)
# 2010-04-15, jkesanen <jani.kesanen@gmail.com>
#   version 0.3: - added output formatting
#                - removed output and city color related options
# 2010-04-09, jkesanen <jani.kesanen@gmail.com>
#   version 0.2.1: - added support for different languages
# 2010-04-07, jkesanen <jani.kesanen@gmail.com>
#   version 0.2: - fetch weather using non-blocking hook_process interface
# 2010-04-06, jkesanen <jani.kesanen@gmail.com>
#   version 0.1: - initial release.
#

import weechat

from urllib import quote
from xml.dom import minidom
from time import time
from sys import version_info

SCRIPT_NAME    = "yweather"
SCRIPT_AUTHOR  = "Keith Johnson <kj@ubergeek42.com.com>"
SCRIPT_VERSION = "0.5"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Bar item with current Yahoo weather"

# Script options
settings = {
    # City to monitor (as a woeid, see http://en.wikipedia.org/wiki/WOEID)
    'city'           : '',
    # Temperature units (c or f)
    'unit'           : 'c',
    # Update interval in minutes
    'interval'       : '10',
    # Timeout in seconds for fetching weather data
    'timeout'        : '10',
    # The color of the output
    'output_color'   : 'white',
    # Formatting (%C = city, %D = degrees, %O = condition)
    'format'         : '%C: %D, %O',
}

# Timestamp for the last update
last_run = 0

# The last city and format for the need of refresh
last_city = ''
last_format = ''

# Cached copy of the last successful output
yweather_output = 'Loading...'

yweather_hook_process = ''
yweather_stdout = ''

YAHOO_WEATHER_URL = 'http://weather.yahooapis.com/forecastrss?w=%s&u=%s'
YAHOO_WEATHER_NS = 'http://xml.weather.yahoo.com/ns/rss/1.0'
def parse_yahoo_weather_rss(xml_response):
    '''
    Parses the relevant weather data from the Yahoo rss

    Returns:
      weather_data: a dictionary information to be displayed
    '''
    try:
        dom = minidom.parseString(xml_response)
    except:
        return

    # Get the tags from the xml document
    ylocation = dom.getElementsByTagNameNS(YAHOO_WEATHER_NS, 'location')[0]
    ycondition = dom.getElementsByTagNameNS(YAHOO_WEATHER_NS, 'condition')[0]

    # Build our data structure to store the information
    weather_data = {}
    weather_data['location']  = ylocation.getAttribute('city') + ", " + ylocation.getAttribute('region');
    weather_data['condition'] = ycondition.getAttribute('text');
    weather_data['temp']      = ycondition.getAttribute('temp') + weechat.config_get_plugin('unit');

    # Cleanup
    dom.unlink()
    return weather_data


def format_weather(weather_data):
    '''
    Formats the weather data for display in the bar item

    Returns:
      output: a string of formatted weather data.
    '''
    output = weechat.color(weechat.config_get_plugin('output_color')) + weechat.config_get_plugin('format')
    output = output.replace('%C', weather_data['location'])

    temp = 'N/A'
    condition = 'N/A'

    if weather_data:
        temp = weather_data['temp'].encode('utf-8')
        if weather_data.has_key('condition'):
            condition = weather_data['condition'].encode('utf-8')

    output = output.replace('%D', temp)
    output = output.replace('%O', condition)

    output += weechat.color('reset')

    return output


def yweather_data_cb(data, command, rc, stdout, stderr):
    '''
    Callback for the data fetching process.
    '''
    global last_city, last_run, last_format
    global yweather_hook_process, yweather_stdout, yweather_output

    if rc == weechat.WEECHAT_HOOK_PROCESS_ERROR or stderr != '':
        weechat.prnt('', '%syweather: Weather information fetching failed: %s' % (\
            weechat.prefix("error"), stderr))
        return weechat.WEECHAT_RC_ERROR

    if stdout:
        yweather_stdout += stdout

    if int(rc) < 0:
        # Process not ready
        return weechat.WEECHAT_RC_OK

    # Update status variables for succesful run
    last_run = time()
    last_city = weechat.config_get_plugin('city')
    last_format = weechat.config_get_plugin('format')
    yweather_hook_process = ''

    if not yweather_stdout:
        return weechat.WEECHAT_RC_OK

    try:
        # The first row should contain "content-type" from HTTP header
        content_type, xml_response = yweather_stdout.split('\n', 1)
    except:
        # Failed to split received data in two at carridge return
        weechat.prnt('', '%syweather: Invalid data received' % (weechat.prefix("error")))
        yweather_stdout = ''
        return weechat.WEECHAT_RC_ERROR

    yweather_stdout = ''

    # Determine the used character set in the response
    try:
        charset = content_type.split('charset=')[1]
    except:
        charset = 'utf-8'

    if charset.lower() != 'utf-8':
        xml_response = xml_response.decode(charset).encode('utf-8')

    # Feed the respose to parser and parsed data to formatting
    weather_data = parse_yahoo_weather_rss(xml_response)
    yweather_output = format_weather(weather_data)

    # Request bar item to update to the latest "yweather_output" 
    weechat.bar_item_update('yweather')

    return weechat.WEECHAT_RC_OK


def yweather_cb(*kwargs):
    ''' Callback for the Yahoo weather bar item. '''
    global last_run, last_city, last_format
    global yweather_output, yweather_hook_process

    # Nag if user has not specified the city
    if not weechat.config_get_plugin('city'):
        return 'SET CITY'

    # Use cached copy if it is updated recently enough
    if weechat.config_get_plugin('city') == last_city and \
       weechat.config_get_plugin('format') == last_format and \
       (time() - last_run) < (int(weechat.config_get_plugin('interval')) * 60):
        return yweather_output

    location_id, unit = map(quote, (weechat.config_get_plugin('city'), \
                                  weechat.config_get_plugin('unit')))
    url = YAHOO_WEATHER_URL % (location_id, unit)

    command = 'urllib2.urlopen(\'%s\')' % (url)

    if yweather_hook_process != "":
        weechat.unhook(yweather_hook_process)
        yweather_hook_process = ''

    # Fire up the weather informationg fetching
    python2_bin = weechat.info_get("python2_bin", "") or "python"
    yweather_hook_process = weechat.hook_process(\
        python2_bin + " -c \"import urllib2;\
                     handler = " + command + ";\
                     print handler.info().dict['content-type'];\
                     print handler.read();\
                     handler.close();\"",
        int(weechat.config_get_plugin('timeout')) * 1000, "yweather_data_cb", "")

    # The old cached string is returned here. yweather_data_cb() will 
    # request a new update after the data is fetched and parsed.
    return yweather_output


def yweather_update(*kwargs):
    weechat.bar_item_update('yweather')
    return weechat.WEECHAT_RC_OK


if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, '', ''):
    for option, default_value in settings.iteritems():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, default_value)

    weechat.bar_item_new('yweather', 'yweather_cb', '')
    weechat.bar_item_update('yweather')
    weechat.hook_timer(int(weechat.config_get_plugin('interval')) * 1000 * 60,
            0, 0, 'yweather_update', '')
