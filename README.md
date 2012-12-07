Weechat Scripts
==========
Assorted scripts for weechat, the command line irc client.

## yweather.py
This is a modified version of jkesanen's gweather.py script.  Since Google deprecated their "unofficial" weather api, it was no longer working.  This version uses [Yahoo's Weather API](http://developer.yahoo.com/weather/) to pull data.

### A note about location:
Yahoo's weather api requires a WOEID rather than a city name/zip code.  A WOEID is a unique number that defines a location.  A useful site for searching for a location to find it's WOEID is http://woeid.rosselliot.co.nz/.

#### Special Thanks
* jkesanen - Author of the gweather.py script
* FlashCode - For creating weechat