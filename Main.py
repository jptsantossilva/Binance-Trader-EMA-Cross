# %%
import os
import pandas as pd
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
import requests
from datetime import datetime,timezone
import time
import sys

# %%
# create .bat file that will run python program

# %%
#criar csv das orders
# orders = client.get_all_orders(symbol='BTCBUSD', limit=1)
# dforders = pd.DataFrame(orders)
# # colunas a manter
# col_keep = ['symbol','price','executedQty','side','time']
# dforders = dforders[col_keep]
# dforders.time = pd.to_datetime(dforders.time, unit='ms')
# dforders.to_csv('orders.csv', mode='a', index=False, header=False)

# %%
# create initial csv with positions
# posframe = pd.DataFrame(symbols)
# posframe.columns = ['Currency']
# posframe['position'] = 0
# posframe['quantity'] = 0
# posframe.to_csv('positioncheck', index=False)

# %%
# environment variables
try:
    # Binance
    api_key = os.environ.get('binance_api')
    # print("api_key: ", api_key)
    api_secret = os.environ.get('binance_secret')
    
    # Telegram
    telegramToken = os.environ.get('telegramToken') 
    telegram_chat_id = os.environ.get('telegram_chat_id')

except KeyError: 
    print("Environment variable does not exist")

# %%
# read positions csv
posframe = pd.read_csv('positioncheck')
# posframe

# read orders csv
# we just want the header, there is no need to get all the existing orders.
# at the end we will append the orders to the csv
dforders = pd.read_csv('orders', nrows=0)
# dforders

# %%
# constants

# coins to trade
symbols = ['BTCBUSD','ETHBUSD','BNBBUSD','SOLBUSD','MATICBUSD','FTTBUSD']

# strategy
timeframe = Client.KLINE_INTERVAL_1HOUR # "1h"

# percentage of balance to open position for each trade - example 0.1 = 10%
tradepercentage = float("0.002")
minPositionSize = 20 # minimum position size in usd
# risk percentage per trade - example 0.01 = 1%
risk = float("0.01")

# Telegram
url = f"https://api.telegram.org/bot{telegramToken}/getUpdates"
# print(requests.get(url).json())

# emoji
eStart   = u'\U000025B6'
eStop    = u'\U000023F9'
eWarning = u'\U000026A0'
eEnterTrade = u'\U0001F91E' #crossfingers
eExitTrade  = u'\U0001F91E' #crossfingers
eTradeWithProfit = u'\U0001F44D' # thumbs up
eTradeWithLoss   = u'\U0001F44E' # thumbs down
eInformation = u'\U00002139'


# %%
def sendTelegramMessage(emoji, msg):
    lmsg = emoji+" "+msg
    url = f"https://api.telegram.org/bot{telegramToken}/sendMessage?chat_id={telegram_chat_id}&text={lmsg}"
    requests.get(url).json() # this sends the message

def sendTelegramAlert(emoji, date, coin, timeframe, strategy, ordertype, value, amount):
    lmsg = emoji + " " + str(date) + " - " + coin + " - " + strategy + " - " + timeframe + " - " + ordertype + " - " + "Value: " + str(value) + " - " + "Amount: " + str(amount)
    url = f"https://api.telegram.org/bot{telegramToken}/sendMessage?chat_id={telegram_chat_id}&text={lmsg}"
    requests.get(url).json() # this sends the message

# %%
# def testTelegramMessages():
    # sendTelegramMessage(eInformation," Environment variable does not exist")
# testTelegramMessages()

# %%
# Binance Client
client = Client(api_key, api_secret)

# %%
def calcPositionSize():

    # get balance from BUSD
    stableBalance = client.get_asset_balance(asset='BUSD')['free']
    stableBalance = float(stableBalance)
    # print(stableBalance)

    # calculate position size based on the percentage per trade
    positionSize = stableBalance*tradepercentage 
    positionSize = round(positionSize, 8)
    
    if positionSize < minPositionSize:
        positionSize = minPositionSize

    # positionAmount = 10
    return positionSize

# %%
def getdata(symbol):
    
    frame = pd.DataFrame(client.get_historical_klines(symbol,
                                                    timeframe,
                                                    '200 hour ago UTC'))

    frame = frame[[0,4]]
    frame.columns = ['Time','Close']
    frame.Close = frame.Close.astype(float)
    frame.Time = pd.to_datetime(frame.Time, unit='ms')
    return frame

# %%


# %%
def applytechnicals(df):
    df['FastSMA'] = df.Close.rolling(50).mean()
    df['SlowSMA'] = df.Close.rolling(200).mean()

# %%
def changepos(curr, order, buy=True):
    if buy:
        posframe.loc[posframe.Currency == curr, 'position'] = 1
        posframe.loc[posframe.Currency == curr, 'quantity'] = float(order['executedQty'])
    else:
        posframe.loc[posframe.Currency == curr, 'position'] = 0
        posframe.loc[posframe.Currency == curr, 'quantity'] = 0

    posframe.to_csv('positioncheck', index=False)


# %%
def trader():

    # check open positions and SELL if conditions are fulfilled 
    for coin in posframe[posframe.position == 1].Currency:
        df = getdata(coin)
        applytechnicals(df)
        lastrow = df.iloc[-1]
        if lastrow.SlowSMA > lastrow.FastSMA:
            order = client.create_order(symbol=coin,
                                        side=Client.SIDE_SELL,
                                        type=Client.ORDER_TYPE_MARKET,
                                        quantity = posframe[posframe.Currency == coin].quantity.values[0])
            changepos(coin,order,buy=False)
            
            #add new row to end of DataFrame
            dforders.loc[len(dforders.index)] = [coin, order['price'], order['executedQty'], order['side'], pd.to_datetime(order['transactTime'], unit='ms'),]
            
            # print(order)
            # sendTelegramMessage(eExitTrade, order)
            sendTelegramAlert(eExitTrade,
                            # order['transactTime']
                            pd.to_datetime(order['transactTime'], unit='ms'), 
                            order['symbol'], 
                            timeframe, 
                            "SMA 50-200 CROSS",
                            order['side'],
                            order['price'],
                            order['executedQty'])

    # check coins not in positions and BUY if conditions are fulfilled
    for coin in posframe[posframe.position == 0].Currency:
        df = getdata(coin)
        applytechnicals(df)
        lastrow = df.iloc[-1]
        if lastrow.FastSMA > lastrow.SlowSMA:
            positionSize = calcPositionSize()
            # print("positionSize: ", positionSize)
            order = client.create_order(symbol=coin,
                                        side=Client.SIDE_BUY,
                                        type=Client.ORDER_TYPE_MARKET,
                                        quoteOrderQty = positionSize)
            changepos(coin,order,buy=True)
            
            #add new row to end of DataFrame
            dforders.loc[len(dforders.index)] = [coin, order['price'], order['executedQty'], order['side'], pd.to_datetime(order['transactTime'], unit='ms'),]
                      
            # print(order)
            # sendTelegramMessage(eEnterTrade, order)
            sendTelegramAlert(eEnterTrade,
                            # order['transactTime'], 
                            pd.to_datetime(order['transactTime'], unit='ms'),
                            order['symbol'], 
                            timeframe, 
                            "SMA 50-200 CROSS",
                            order['side'],
                            order['price'],
                            order['executedQty'])
        else:
            print(f'Buying condition for {coin} is not fulfilled')


# %%
# qtd = posframe[posframe.Currency == 'BTCBUSD'].quantity.values[0]
# qtd
# qtd = 0.00054
# order2 = client.create_order(symbol='BTCBUSD',
#                                         side=Client.SIDE_SELL,
#                                         type=Client.ORDER_TYPE_MARKET,
#                                         quantity = qtd)
# print(order2)

# %%
# MIN_NOTIONAL error
# info = client.get_symbol_info('BTCBUSD')
# print(info)
# print(info['filters'][2]['minQty'])
# 0.00001

# %%
try:
    # inform that is running
    # now = datetime.now()
    # dt_string = now.strftime("%d-%m-%Y %H:%M:%S")
    sendTelegramMessage(eStart,"Binance Trader Bot - Started")

    trader()

    # add orders to csv file
    dforders.time = pd.to_datetime(dforders.time, unit='ms')
    dforders.to_csv('orders', mode='a', index=False, header=False)

    # inform that ended
    sendTelegramMessage(eStop, "Binance Trader Bot - Ended")
    
except BinanceAPIException as e:
    print(e.status_code, e.message)
    sendTelegramMessage(eWarning, "Oops! Error code:"+ str(e.status_code) + " - " + e.message)
    sendTelegramMessage(eWarning, "Oops! "+ str(sys.exc_info()[0])+ " occurred.")
    print("Oops!", sys.exc_info()[0], "occurred.")
except BinanceOrderException as e:
    # error handling goes here
    print(e)



