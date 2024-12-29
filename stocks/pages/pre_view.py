from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import View
# from pages.socket_client import *
import requests
import urllib.parse
import json
import numpy as np
import pandas as pd
import logging

def home_view(requests):
    return render(requests, "home.html", {})


averages = []
total = 0
df = None
dict_bs = None
calls_to_single = 0
initial_price = None
logging.basicConfig(filename='stocks_log.log',filemode='a', format='%(name)s - %(levelname)s - %(message)s')
logging.info('Logging started...')

class ChartView(View):

    def get_access_token(self, code):
        # only works first time then it gives error as access_token can only generated once
        apiKey = '5a703f38-6ffa-4342-8333-1ddbe135963c'
        secretKey = 'gknqxlbtv6'
        rurl = urllib.parse.quote('https://127.0.0.1:5000/', safe='')
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        data = f'code={code}&client_id={apiKey}&client_secret={secretKey}&redirect_uri={rurl}&grant_type=authorization_code'
        
        response = requests.post('https://api.upstox.com/v2/login/authorization/token', headers=headers, data=data)
        json_response = response.json()
        # print(json_response)
        return json_response['access_token']

    def live_market_feed(self):
        code = '6IfTV-' 
        # access_token = get_access_token(code)
        # access_token needs to be generated daily
        access_token = 'eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI3NUFDMkIiLCJqdGkiOiI2NjE4Yjc1MDY3N2U1YTZkYTM3MmE1YjEiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNBY3RpdmUiOnRydWUsInNjb3BlIjpbImludGVyYWN0aXZlIiwiaGlzdG9yaWNhbCJdLCJpYXQiOjE3MTI4OTU4MjQsImlzcyI6InVkYXBpLWdhdGV3YXktc2VydmljZSIsImV4cCI6MTcxMjk1OTIwMH0.qjXlhIpwWZFXZ5oDUe3m66DfMSB7_C2nxrcmAUFf7FY'
        # url = 'https://api.upstox.com/v2/market-quote/quotes?instrument_key=NSE_INDEX%7CNifty%2050'
        url = 'https://api.upstox.com/v2/market-quote/quotes?instrument_key=NSE_EQ%7CINE002A01018'

        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }

        response = requests.get(url, headers=headers)
        # print(response.json())
        key = list(response.json()['data'].keys())[0]
        data = response.json()['data'][key]
        ts = data['timestamp']
        ltp = data['last_price']
        avg = data['average_price']
        opening_p = data['ohlc']['open']
        high_p = data['ohlc']['high']
        low_p = data['ohlc']['low']
        close_p = data['ohlc']['close']
        return (data , ts, ltp, avg, opening_p, high_p, low_p, close_p)

    def running_average(self, data, total):
        for value in data:
            total += value
            averages.append(total / (len(averages) + 1))  # Add 1 to avoid division by zero initially
        return total

    def calculate_rsi(self, df, window=14):
        df['Change'] = df['Close'].diff()
        df['Gain'] = np.where(df['Change'] > 0, df['Change'], 0)
        df['Loss'] = np.where(df['Change'] < 0, abs(df['Change']), 0)
        df['Avg Gain'] = df['Gain'].rolling(window=window).mean()
        df['Avg Loss'] = df['Loss'].rolling(window=window).mean()
        df['RS'] = df['Avg Gain'] / df['Avg Loss']
        df['RSI'] = 100 - (100 / (1 + df['RS']))
        return df


    def calculate_rsi_single(self, new_close, df, window=14):
        if len(df) >= window:  # Check if there are enough historical data points
            # Use the last 'window' number of data points for calculation
            last_window_data = df.iloc[-window:]
            change = new_close - last_window_data['Close'].iloc[-1]
            gain = max(0, change)
            loss = abs(min(0, change))
            avg_gain = (last_window_data['Avg Gain'].sum() + gain) / window
            avg_loss = (last_window_data['Avg Loss'].sum() + loss) / window
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        else:
            change = np.nan
            gain = np.nan
            loss = np.nan
            avg_gain = np.nan
            avg_loss = np.nan
            rs = np.nan
            rsi = np.nan 
        df.at[len(df)-1, 'Change'] = change
        df.at[len(df)-1, 'Gain'] = gain
        df.at[len(df)-1, 'Loss'] = loss
        df.at[len(df)-1, 'Avg Gain'] = avg_gain
        df.at[len(df)-1, 'Avg Loss'] = avg_loss
        df.at[len(df)-1, 'RS'] = rs
        df.at[len(df)-1, 'RSI'] = rsi
        return rsi, df


    
    def calculate_bollinger_bands(self, df):
        window = 20
        df['MA'] = df['Close'].rolling(window=window).mean()
        df['STD'] = df['Close'].rolling(window=window).std()
        df['Upper Band'] = df['MA'] + (2 * df['STD'])
        df['Lower Band'] = df['MA'] - (2 * df['STD'])
        calls_to_single = 0
        return df

    # increasing window size due to frequent calling and time difference being only 5 seconds
    def calculate_bollinger_bands_single(self, df, calls_to_single, window=20):
        calls_to_single = calls_to_single+1
        window = window + calls_to_single
        if calls_to_single > 240: # 5*240sec = 20min
            window = 240
        if len(df) >= window:  # Check if there are enough historical data points
            # Use the last 'window' number of data points for calculation
            last_window_data = df.iloc[-window:]
            ma = last_window_data['Close'].mean()
            std = last_window_data['Close'].std()
            upper_band = ma + (2 * std)
            lower_band = ma - (2 * std)
        else:
            print('giving np.nan...')
            ma = np.nan
            std = np.nan
            upper_band = np.nan
            lower_band = np.nan
        df.at[len(df)-1, 'MA'] = ma
        df.at[len(df)-1, 'STD'] = std
        df.at[len(df)-1, 'Upper Band'] = upper_band
        df.at[len(df)-1, 'Lower Band'] = lower_band
        return ma, std, upper_band, lower_band, df, calls_to_single


    def buy_sell_print(self, dict_bs, price, initial_price):
        window_size = 5
        total_buy = 0
        total_sell = 0
        total_bq = 0
        total_sq = 0
        
        if price <= 50:
            rbq = 1000000 # 10 lac
        elif price > 50 and price <= 100:
            rbq = 500000 
        elif price > 100 and price <= 500:
            rbq = 100000
        elif price > 500 and price <= 1000:
            rbq = 50000
        elif price > 1000 and price <= 5000:
            rbq = 10000
        elif price > 5000 and price <= 10000:
            rbq = 5000
        elif price > 10000 and price <= 50000:
            rbq = 1000
        elif price > 50000 and price <= 100000:
            rbq = 500
        else:
            rbq = 100
         
        for i in range(1, window_size+1):
            # {'quantity': 4, 'price': 2963.55, 'orders': 3}
            total_buy = total_buy+dict_bs['buy'][-i]['price']
            total_sell = total_sell+dict_bs['sell'][-i]['price']
            total_bq = total_bq+dict_bs['buy'][-i]['quantity']
            total_sq = total_sq+dict_bs['sell'][-i]['quantity']
        avg_buy = total_buy/window_size
        avg_sell = total_sell/window_size
        rbq = 2000
        prcnt = 0.1  # 10%
        action = 'hold'
        if (avg_buy > avg_sell and total_bq > total_sq and total_bq > rbq): #or (price > prcnt*initial_price):
            action = 'buy'
            print('Buy!!!')
            # print(f'avg buy: {avg_buy}, avg sell: {avg_sell}')
            # print(f'total bq: {total_bq}, total sq{total_sq}')
            string = 'Buy!!!\n' + f'avg buy: {avg_buy}, avg sell: {avg_sell}\n' + f'total bq: {total_bq}, total sq{total_sq}\n'
            logging.info(string)
 
        elif avg_buy < avg_sell and total_bq < total_sq and total_sq > rbq:
            print('Sell!!!')
            action = 'sell'
            
            # print(f'avg buy: {avg_buy}, avg sell: {avg_sell}')
            # print(f'total bq: {total_bq}, total sq: {total_sq}')
            string = 'Sell!!!\n' + f'avg buy: {avg_buy}, avg sell: {avg_sell}\n' + f'total bq: {total_bq}, total sq{total_sq}\n'
            logging.info(string)
        else: 
            logging.info('Hold...')
            print('Hold....')
        
        return {'action':action, 'avg buy':avg_buy, 'avg sell': avg_sell, 'total bq':total_bq,'total sq': total_sq, 'rbq': rbq}    


    def get(self, request):
        global averages
        global total
        global df
        global dict_bs
        global calls_to_single
        global initial_price
        # print('=======================')
        # print(total)
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest': # Check if it's an AJAX request
            print('fetching live data...')
            # print(df)
            data , ts, ltp, avg, opening_p, high_p, low_p, close_p = self.live_market_feed()
            total += ltp

            averages.append(total/(len(averages)+1))
            if avg is None:
                avg=ltp
            
            # adding a new row
            new_row = [close_p, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan]
            df.loc[len(df)] = new_row
            
            ma, std, upper_band, lower_band, df, calls_to_single = self.calculate_bollinger_bands_single(df, calls_to_single)
            rsi,df = self.calculate_rsi_single(close_p, df)
            
            # 'buy': [{'quantity': 11, 'price': 2963.65, 'orders': 3},
            #    {'quantity': 4, 'price': 2963.55, 'orders': 3},
            #    {'quantity': 18, 'price': 2963.5, 'orders': 5},
            #    {'quantity': 1, 'price': 2963.4, 'orders': 1},
            #    {'quantity': 1, 'price': 2963.3, 'orders': 1}],
            
            buys = data['depth']['buy'] 
            sells = data['depth']['sell']
            price = data['last_price']
            dict_bs['buy'].extend(buys)
            dict_bs['sell'].extend(sells)
            # print(dict_bs)
            action, avg_buy, avg_sell, total_bq, total_sq, rbq = self.buy_sell_print(dict_bs, price, initial_price)
            
            buy_or_sell = {
                'action': action, 
                'avg_buy': avg_buy,
                'avg_sell': avg_sell,
                'total_bq': total_bq,
                'total_sq': total_sq, 
                'rbq': rbq
            }

            indicators = {
                'rsi':rsi,
                'bollinger_bands': {
                    'ma': ma,
                    'upper_band': upper_band,
                    'lower_band': lower_band,             
                }
            }
            context_data = {
                'x':ts,
                'y':ltp,
                'avg':avg,
                'run_avg':averages[-1],
                'customdata': [opening_p, high_p, low_p],
                'indicators': indicators,
                'buy_or_sell': buy_or_sell,
            }
            return JsonResponse({'data':context_data})

        else:
            # print('===============================================')
            # print(request)

            # url = "https://api.upstox.com/v2/historical-candle/intraday/NSE_INDEX%7CNifty%2050/1minute/"
            url = 'https://api.upstox.com/v2/historical-candle/intraday/NSE_EQ%7CINE002A01018/1minute'
            # url = 'https://api.upstox.com/v2/historical-candle/NSE_EQ%7CINE002A01018/1minute/2024-04-10/2024-04-10'

            headers = {"Accept": "application/json"}
            name = 'Stock Price'
            if "NSE_EQ%7CINE002A01018" in url: 
                name = 'Reliance'

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()["data"]["candles"]

                x = []
                avg = []
                closing_p = []
                customdata = []
                opening_p = []
                high_p = []
                low_p = []

                for candle in data:
                    x.append(candle[0])
                    avg.append((candle[2]+candle[3])/2)
                    closing_p.append(candle[4])
                    opening_p.append(candle[1])
                    high_p.append(candle[2])
                    low_p.append(candle[3])
                    customdata.append([opening_p[-1], high_p[-1], low_p[-1]])

                buys = []
                sells = []
                dict_bs = {
                    'buy':buys, 
                    'sell': sells
                }
                
                x = list(reversed(x))
                avg = list(reversed(avg))

                customdata = list(reversed(customdata))
                closing_p = list(reversed(closing_p))
                total = self.running_average(closing_p, total)
                run_avg = averages

                initial_price = closing_p[0]
                df = pd.DataFrame({"Close": closing_p})
                # print(df)
                df = self.calculate_rsi(df)
                df = self.calculate_bollinger_bands(df)
                rsi = df['RSI'].replace(np.nan, None)
                ma = df['MA'].replace(np.nan, None)
                upper_band  = df['Upper Band'].replace(np.nan, None)
                lower_band = df['Lower Band'].replace(np.nan, None)

                rsi = rsi.tolist()
                ma = ma.tolist()
                upper_band = upper_band.tolist()
                lower_band = lower_band.tolist()

                indicators = {
                    'rsi':rsi,
                    'bollinger_bands': {
                        'ma': ma,
                        'upper_band': upper_band,
                        'lower_band': lower_band,             
                    }
                }

                context_data = {
                    "x": x, 
                    "y": closing_p, 
                    "run_avg": run_avg, 
                    "avg":avg, 
                    "customdata":customdata, 
                    "indicators": indicators}
                # print('df before single data points: \n', df)

                context_data = json.dumps(context_data)
            else:
                print(f"Error: {response.status_code} - {response.text}")
            # print(df)
            # print('printing at the end....')
            return render(request, "stock_page.html", {"data": context_data, "name": name})
