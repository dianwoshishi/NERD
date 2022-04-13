#!/usr/bin/env python
# -*- coding: utf-8 -*-
# description: https://stat.ripe.net/docs/data_api
import copy
import json

from datetime import datetime, timedelta
from enum import Enum
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network
from typing import TypeVar, Optional, Dict, Any

import requests


from dateutil.parser import parse

IPTypes = TypeVar('IPTypes', IPv4Address, IPv6Address, 'str')
PrefixTypes = TypeVar('PrefixTypes', IPv4Network, IPv6Network, 'str')
TimeTypes = TypeVar('TimeTypes', datetime, 'str')


class ASNsTypes(Enum):
    transiting = 't'
    originating = 'o'
    all_types = 't,o'
    undefined = ''


class AddressFamilies(Enum):
    ipv4 = 'v4'
    ipv6 = 'v6'
    all_families = 'v4,v6'
    undefined = ''


class Noise(Enum):
    keep = 'keep'
    remove = 'filter'


class StatsRIPE():

    def __init__(self, sourceapp='bgpranking-ng - CIRCL'):
        self.url = "https://stat.ripe.net/data/{method}/data.json?{parameters}"
        self.sourceapp = sourceapp

    def __time_to_text(self, query_time: TimeTypes) -> str:
        if isinstance(query_time, datetime):
            return query_time.isoformat()
        return query_time

    def _get(self, method: str, parameters: Dict) -> Dict:
        parameters['sourceapp'] = self.sourceapp

        url = self.url.format(method=method, parameters='&'.join(['{}={}'.format(k, str(v).lower()) for k, v in parameters.items()]))
        response = requests.get(url)
        j_content = response.json()
        return j_content

    def network_info(self, ip: IPTypes) -> dict:
        parameters = {'resource': ip}
        return self._get('network-info', parameters)

    def AS_info(self, asn: int) -> dict:
        parameters = {'resource': str(asn)}
        return self._get('as-overview', parameters)

    def Reverse_DNS_IP(self, ip: IPTypes) -> dict:
        parameters = {'resource': ip}
        return self._get('reverse-dns-ip', parameters)

    def Search(self, item: str, limit: int=6) -> dict:
        parameters = {'resource': item, 'limit':limit}
        return self._get('searchcomplete', parameters)

    def Atlas_Probes(self, prefix_asn_country: str):
        parameters = {'resource': prefix_asn_country}
        return self._get('atlas-probes', parameters)

    def prefix_overview(self, prefix: PrefixTypes, min_peers_seeing: int= 0,
                        max_related: int=0, query_time: Optional[TimeTypes]=None) -> dict:
        parameters: Dict[str, Any] = {'resource': prefix}
        if min_peers_seeing:
            parameters['min_peers_seeing'] = min_peers_seeing
        if max_related:
            parameters['max_related'] = max_related
        if query_time:
            parameters['query_time'] = self.__time_to_text(query_time)
        return self._get('prefix-overview', parameters)

    def ris_asns(self, query_time: Optional[TimeTypes]=None, list_asns: bool=False, asn_types: ASNsTypes=ASNsTypes.undefined):
        parameters: Dict[str, Any] = {}
        if list_asns:
            parameters['list_asns'] = list_asns
        if asn_types:
            parameters['asn_types'] = asn_types.value
        if query_time:
            parameters['query_time'] = self.__time_to_text(query_time)
        return self._get('ris-asns', parameters)

    def ris_prefixes(self, asn: int, query_time: Optional[TimeTypes]=None,
                     list_prefixes: bool=False, types: ASNsTypes=ASNsTypes.undefined,
                     af: AddressFamilies=AddressFamilies.undefined, noise: Noise=Noise.keep):
        parameters: Dict[str, Any] = {'resource': str(asn)}
        if query_time:
            parameters['query_time'] = self.__time_to_text(query_time)
        if list_prefixes:
            parameters['list_prefixes'] = list_prefixes
        if types:
            parameters['types'] = types.value
        if af:
            parameters['af'] = af.value
        if noise:
            parameters['noise'] = noise.value
        return self._get('ris-prefixes', parameters)

    def country_asns(self, country: str, details: int=0, query_time: Optional[TimeTypes]=None):
        parameters: Dict[str, Any] = {'resource': country}
        if details:
            parameters['lod'] = details
        if query_time:
            parameters['query_time'] = self.__time_to_text(query_time)
        return self._get('country-asns', parameters)


if __name__ == "__main__":
    ripe = StatsRIPE()
    country = 'cn'
    # response = ripe.country_asns(country, query_time=datetime.today().date(), details=1)
    # response = ripe.ris_prefixes(4538, query_time=datetime.today().date())
    # response = ripe.network_info("8.8.8.8")
    # response = ripe.Reverse_DNS_IP("8.8.8.8")
    # response = ripe.AS_info(1)
    # response = ripe.Search("AS4538")
    # response = ripe.Atlas_Probes("AS4538")
    response = ripe.prefix_overview("109.0.0.0/11")
    print(response["data"])