#!/opt/hts/bin/python2.7
# -*- coding: utf-8 -*-

import sys
import time
import base64
from hmac import new
import httplib

from hashlib import sha512
from time import time
from json import loads, dumps

from error import ERROR_MAP

class Coin():
    HEADER = {
        'Content-type': 'application/json'
    }

    def __init__(self, host):
        self.host = host
        self.conn = httplib.HTTPSConnection(host=host, port=443)
        self.config = {}

        for line in open('coin.conf', 'r').read().splitlines():
            try:
                key, value = [x.strip() for x in line.split('=')]
                self.config[key] = value
            except: # abnormal configuration
                break

        self.body = {
            'access_token': self.config['access-token']
        }

    def getEncodePayload(self, payload):
        payload[u'nonce'] = int(time()*1000)
        dumpedJson = dumps(payload)
        encodeJson = base64.b64encode(dumpedJson)

        return encodeJson

    def getSign(self, payload):
        signature = new(str(self.config['secret-key']).upper(), str(payload), sha512)
        return signature.hexdigest()

    def getResponse(self, url, method='POST', header={}, body={}):
        header.update(self.HEADER)
        body.update(self.body)
        #print body
        payload = self.getEncodePayload(body)
        header['X-COINONE-PAYLOAD'] = payload
        header['X-COINONE-SIGNATURE'] = self.getSign(payload)

        self.conn.request(method, url, headers=header, body=payload)
        resp = self.conn.getresponse()
        temp = resp.read()
        try:
            content = eval(temp)
        except:
            print 'invalid request url'
            content = {'errorCode': '999'}

        errCode = content.get('errorCode')
        if errCode != '0':
            print errCode, ERROR_MAP.get(errCode)

        return content

if __name__ == '__main__':
    host = 'api.coinone.co.kr'
    statusValue = 15.0 # safe/dangerous 구분을 위한 constant
    wallet = {}
    coinInfo = {}

    coin = Coin(host)
    if not coin.config:
        sys.exit(1)

    url = '/v2/account/balance/'
    result = coin.getResponse(url)

    for k, v in result.viewitems():
        if k == 'krw':
            continue
        if not isinstance(v, dict):
            continue
        wallet[k] = v

    if not wallet:
        print 'Coin does not exists which balance is zero.'
        sys.exit(1)

    url = '/trades'
    for coinName in wallet.keys():
        result = coin.getResponse(url + '?currency=%s' % coinName, method='GET')
        coinInfo[coinName] = result['completeOrders']

    for coinName, completeOrders in coinInfo.viewitems():
        wallet[coinName]['volume'] = sum([eval(x['price'])*eval(x['qty']) for x in completeOrders])
        min = int(completeOrders[0]['price'])
        max = 0
        for item in completeOrders:
            price = int(item['price']) # short-cut
            if min > price:
                min = price
            if max < price:
                max = price

        current = float(completeOrders[-1]['price'])
        difference = float(max-min)
        percent = difference/current*100
        wallet[coinName]['current'] = current
        wallet[coinName]['difference'] = difference
        wallet[coinName]['status'] = 'stable' if abs(percent) < statusValue else 'unstable'

    for coinName, info in wallet.viewitems():
        print '='*30
        print coinName
        print '='*30
        for k, v in info.viewitems():
            print '%s : %s' % (k, v)

# EOF
