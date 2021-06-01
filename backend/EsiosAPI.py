#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 20 11:42:56 2020
@author: jjprz
"""

import requests, json
import logging
from datetime import datetime, timedelta

class Ree():
    
    def __init__(self, debug_level=logging.INFO):
        logging.getLogger().setLevel(debug_level)
        
    def get_prices(self, fecha):
        
        strFecha = fecha.strftime("%Y-%m-%d")

        response = requests.get('https://api.esios.ree.es/archives/70/download_json?locale=es&date=' + strFecha)
        precios = json.loads(response.text)
        return precios['PVPC']


        
        