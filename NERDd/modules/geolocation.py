"""
NERD module getting geographical location of an IP address using MaxMind's
GeoLite2 database.

Requirements:
- "geolite2" package

Acknowledgment:
This product includes GeoLite2 data created by MaxMind, available from
http://www.maxmind.com.
"""
import logging

from core.basemodule import NERDModule
import g

import geoip2.database
import geoip2.errors


class Geolocation(NERDModule):
    """
    Geolocation module.
    
    Queries newly added IP addresses in MaxMind's GeoLite2 database to get its
    (approximate) geographical location.
    Stores the following attributes:
      geo.ctry  # Country (2-letter ISO code)
      geo.city  # City (English name)
      geo.tz    # Timezone (Text specification, e.g. 'Europe/Prague')
    
    Event flow specification:
      !NEW -> geoloc -> geo.{ctry,city,tz}
    """
    
    def __init__(self):
        self.log = logging.getLogger("Geolocation")

        # Get DB path
        db_path = g.config.get('geolocation.geolite2_db_path')
        
        # Instantiate DB reader (i.e. open GeoLite database)
        try:
            self._reader = geoip2.database.Reader(db_path)
        except OSError as e:
            self.log.error(f"Can't open GeoLite2 DB file ({e}). Geolocation module will be disabled!")
            return

        g.um.register_handler(
            self.geoloc,
            'ip',
            ('!NEW','!refresh_geo'),
            ('geo.ctry','geo.city','geo.tz')
        )
    
    def geoloc(self, ekey, rec, updates):
        """
        Query GeoLite2 DB to get country, city and timezone of the IP address.
        If address isn't found, don't set anything.
        
        Arguments:
        ekey -- two-tuple of entity type and key, e.g. ('ip', '192.0.2.42')
        rec -- record currently assigned to the key
        updates -- list of all attributes whose update triggerd this call and  
          their new values (or events and their parameters) as a list of 
          2-tuples: [(attr, val), (!event, param), ...]

        
        Returns:
        List of update requests.
        """
        etype, key = ekey
        if etype != 'ip':
            return None
        
        try:
            result = self._reader.city(key)
        except geoip2.errors.AddressNotFoundError:
            return None
        
#         print(result.country)
#         print(result.city)
#         print(result.location)
        ctry = result.country.iso_code
        city = result.city.names.get('en', None)
        tz = result.location.time_zone
        #lon = result.location.longitude
        #lat = result.location.latitude
        
        g.um.update(('ip', key), [
            ('set', 'geo.ctry', ctry),
            ('set', 'geo.city', city),
            ('set', 'geo.tz', tz),
        ])

        return None
        
