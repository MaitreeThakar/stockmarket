from django.http import HttpResponse, JsonResponse, Http404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views.generic import View
import requests
import urllib.parse
import json
import numpy as np
import pandas as pd
import logging
from .models import StockInventory, Trade
from django.db.models import Sum
from datetime import date


def home_view(requests):
    return render(requests, "home.html", {})


dict_list = []
# averages = []
logger = logging.getLogger(__name__)
logger.info("Logging started...")


class ChartView(LoginRequiredMixin, View):
    login_url = "user_login"

    # redirect_field_name = 'page'
    def get(self, request) -> JsonResponse | HttpResponse:
        global dict_list

        instrument_key = ""
        name = ""
        if request.GET:
            symbol = request.GET["symbol"]
            changed = request.GET["changed"]

            # print('symbol'+str(symbol))
            # print('changed'+str(changed))

            match symbol:
                case "reliance":
                    instrument_key = "NSE_EQ%7CINE002A01018"
                    name = "Reliance"
                case "nifty":
                    instrument_key = "NSE_INDEX%7CNifty%2050"
                    name = "Nifty 50"
                case "hdfc":
                    instrument_key = "NSE_EQ|INE040A01034"
                    name = "HDFC Bank"
                case _:
                    instrument_key = "NSE_EQ%7CINE002A01018"
                    name = "Reliance"
        else:
            # print('empty get request')
            symbol = "reliance"
            changed = "false"
            instrument_key = "NSE_EQ%7CINE002A01018"
            name = "Reliance"

        # print('-----------------------------Values----------------------------- ')
        # print(f'Instrument key {instrument_key}')
        # print(f'Name {name}')
        # print(f'Symbol {symbol}')
        # print(f'Changed {changed}')
        # print('\n')

        if (
            changed == "false"
            and request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"
        ):  # Check if it's an AJAX request
            index = -1
            dictionary = {}
            for i in range(len(dict_list)):
                if dict_list[i]["symbol"] == symbol:
                    dictionary = dict_list[i]
                    index = i
            if index == -1:
                # print(dict_list)
                raise Http404("symbol not found in dict_list. Please check...")

            df = dictionary["df"]
            if df is None:
                return JsonResponse({"data": None})

            # print(f'fetching live data...{len(df)}')
            try:
                (
                    data,
                    ts,
                    ltp,
                    avg,
                    opening_p,
                    high_p,
                    low_p,
                    close_p,
                    volume,
                    total_buy_quantity,
                    total_sell_quantity,
                ) = self.live_market_feed(instrument_key)
            except:
                raise Http404(
                    "Error encountered while fetching data from live market feed"
                )
            total = dictionary["total"]
            total += ltp
            averages = dictionary["averages"]
            averages.append(total / (len(averages) + 1))
            volume_cumulative = dictionary["volume_cumulative"]

            # print(dictionary)
            # print('before: '+str(volume))
            volume -= volume_cumulative[-1]
            # print(volume)
            if avg is None:  # for some symbols avg is None
                avg = ltp

            # adding a new row
            new_row = [
                close_p,
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                np.nan,
            ]
            df.loc[len(df)] = new_row

            calls_to_single = dictionary["calls_to_single"]
            ma, upper_band, lower_band, df, calls_to_single = (
                self.calculate_bollinger_bands_single(df, calls_to_single)
            )
            rsi, df = self.calculate_rsi_single(close_p, df)

            buys = data["depth"]["buy"]
            sells = data["depth"]["sell"]
            price = data["last_price"]
            ts = data["timestamp"]

            dict_bs = dictionary["dict_bs"]
            dict_bs["buy"].extend(buys)
            dict_bs["sell"].extend(sells)

            initial_price = dictionary["initial_price"]
            action, avg_buy, avg_sell, total_bq, total_sq, rbq, strength = (
                self.buy_sell_print(dict_bs, ts, price, initial_price, logger)
            )
            # action2 = self.calculate_price2(dict_bs, total_buy_quantity, volume, total_sell_quantity, price)
            buy_or_sell = {
                "action": action,
                "avg_buy": round(avg_buy, 2),
                "avg_sell": round(avg_sell, 2),
                "total_bq": total_bq,
                "total_sq": total_sq,
                "rbq": rbq,
                "strength": strength,
            }

            indicators = {
                "rsi": rsi,
                "bollinger_bands": {
                    "ma": ma,
                    "upper_band": upper_band,
                    "lower_band": lower_band,
                },
            }
            context_data = {
                "x": ts,
                "y": ltp,
                "avg": avg,
                "run_avg": averages[-1],
                "customdata": [opening_p, high_p, low_p],
                "indicators": indicators,
                "buy_or_sell": buy_or_sell,
                "volume": volume,
                "volume_cumulative": volume_cumulative,
            }
            dict_list[index]["averages"] = averages
            dict_list[index]["total"] = total
            dict_list[index]["df"] = df
            dict_list[index]["dict_bs"] = dict_bs
            dict_list[index]["calls_to_single"] = calls_to_single
            dict_list[index]["volume_cumulative"] = volume_cumulative

            return JsonResponse({"data": context_data})

        else:
            # sending full data
            dictionary = {
                "symbol": symbol,
                "averages": [],  # list of averages
                "total": 0,  # sum of current prices
                "df": None,  # data frame to store data candles values
                "dict_bs": None,  # store buy sells, for use in live data calculations
                "calls_to_single": 0,  # calls made to live data
                "initial_price": None,
                "volume_cumulative": 0,
            }

            # print(f'Fetching full data for {symbol}')

            # url = 'https://api.upstox.com/v2/historical-candle/NSE_EQ%7CINE002A01018/1minute/2024-04-16/2024-04-16'
            # url = "https://api.upstox.com/v2/historical-candle/intraday/NSE_INDEX%7CNifty%2050/1minute/"
            # url = 'https://api.upstox.com/v2/historical-candle/intraday/NSE_EQ%7CINE002A01018/1minute'

            url = f"https://api.upstox.com/v2/historical-candle/intraday/{instrument_key}/1minute"
            headers = {"Accept": "application/json"}
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()["data"]["candles"]

                # # print(data)
                x = []
                avg = []
                closing_p = []
                customdata = []
                opening_p = []
                high_p = []
                low_p = []
                volume = []
                volume_cumulative = []

                for candle in data:
                    x.append(candle[0])
                    avg.append((candle[2] + candle[3]) / 2)
                    closing_p.append(candle[4])
                    opening_p.append(candle[1])
                    high_p.append(candle[2])
                    low_p.append(candle[3])
                    customdata.append([opening_p[-1], high_p[-1], low_p[-1]])
                    volume.append(candle[5])

                buys = []
                sells = []
                dict_bs = {"buy": buys, "sell": sells}
                dictionary["dict_bs"] = dict_bs

                x = list(reversed(x))
                avg = list(reversed(avg))

                customdata = list(reversed(customdata))
                closing_p = list(reversed(closing_p))
                volume = list(reversed(volume))

                volume_cumulative = [sum(volume[: i + 1]) for i in range(len(volume))]
                dictionary["volume_cumulative"] = volume_cumulative

                dictionary["total"], dictionary["averages"] = self.running_average(
                    closing_p, dictionary["total"], dictionary["averages"]
                )
                run_avg = dictionary["averages"]

                dictionary["initial_price"] = closing_p[0]

                df = pd.DataFrame({"Close": closing_p})

                df = self.calculate_rsi(df)
                df = self.calculate_bollinger_bands(df)

                dictionary["df"] = df
                dictionary["calls_to_single"] = 0

                rsi = df["RSI"].replace(np.nan, None)
                ma = df["MA"].replace(np.nan, None)
                upper_band = df["Upper Band"].replace(np.nan, None)
                lower_band = df["Lower Band"].replace(np.nan, None)

                rsi = rsi.tolist()
                ma = ma.tolist()
                upper_band = upper_band.tolist()
                lower_band = lower_band.tolist()

                indicators = {
                    "rsi": rsi,
                    "bollinger_bands": {
                        "ma": ma,
                        "upper_band": upper_band,
                        "lower_band": lower_band,
                    },
                }

                context_data = {
                    "x": x,
                    "y": closing_p,
                    "run_avg": run_avg,
                    "avg": avg,
                    "customdata": customdata,
                    "indicators": indicators,
                    "volume": volume,
                    "volume_cumulative": volume_cumulative,
                }
                dict_list.append(dictionary)

            else:
                response = Http404(f"Error: {response.status_code} - {response.text}")
                response.write("This error occured due to api fetch for intraday data")
                raise response

            if changed == "true":
                return JsonResponse({"data": context_data, "name": name})
            context_data = json.dumps(context_data)
            return render(
                request, "stock_page.html", {"data": context_data, "name": name}
            )

    def get_access_token(self, code):
        # only works first time then it gives error as access_token can only generated once
        apiKey = "5a703f38-6ffa-4342-8333-1ddbe135963c"
        secretKey = "gknqxlbtv6"
        rurl = urllib.parse.quote("https://127.0.0.1:5000/", safe="")
        headers = {
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = f"code={code}&client_id={apiKey}&client_secret={secretKey}&redirect_uri={rurl}&grant_type=authorization_code"

        response = requests.post(
            "https://api.upstox.com/v2/login/authorization/token",
            headers=headers,
            data=data,
        )
        json_response = response.json()
        # # print(json_response)
        return json_response["access_token"]

    def live_market_feed(self, instrument_key="NSE_EQ%7CINE002A01018"):
        code = "6IfTV-"
        # access_token = get_access_token(code)
        # access_token needs to be generated daily
        access_token = 'eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI3NUFDMkIiLCJqdGkiOiI2NjQxOThhOTY4ZDE5NjM0ZGFiMzMwYzEiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaWF0IjoxNzE1NTc0OTUzLCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3MTU2Mzc2MDB9.ClhzDmHT_E7mRnyVU_LkezjivroT1CiPCMk9qJHEGOI'
        # url = 'https://api.upstox.com/v2/market-quote/quotes?instrument_key=NSE_INDEX%7CNifty%2050'
        url = f"https://api.upstox.com/v2/market-quote/quotes?instrument_key={instrument_key}"

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        try:
            response = requests.get(url, headers=headers)
            key = list(response.json()["data"].keys())[0]
            data = response.json()["data"][key]
            ts = data["timestamp"]
            ltp = data["last_price"]
            avg = data["average_price"]
            opening_p = data["ohlc"]["open"]
            high_p = data["ohlc"]["high"]
            low_p = data["ohlc"]["low"]
            close_p = data["ohlc"]["close"]
            volume = data["volume"]
            total_buy_quantity = data["total_buy_quantity"]
            total_sell_quantity = data["total_sell_quantity"]
        except requests.exceptions.RequestException as e:
            error_message = f"Error calling live feed API: {str(e)}"
            return JsonResponse({"error": error_message}, status=500)
        except (KeyError, IndexError) as e:
            error_message = f"Unexpected API response format: {str(e)}"
            return JsonResponse({"error": error_message}, status=200)

        return (
            data,
            ts,
            ltp,
            avg,
            opening_p,
            high_p,
            low_p,
            close_p,
            volume,
            total_buy_quantity,
            total_sell_quantity,
        )

    def running_average(self, data, total, averages: list):
        for value in data:
            total += value
            averages.append(
                total / (len(averages) + 1)
            )  # Add 1 to avoid division by zero initially
        return total, averages

    def calculate_rsi(self, df, window=14):
        df["Change"] = df["Close"].diff()
        df["Gain"] = np.where(df["Change"] > 0, df["Change"], 0)
        df["Loss"] = np.where(df["Change"] < 0, abs(df["Change"]), 0)
        df["Avg Gain"] = df["Gain"].rolling(window=window).mean()
        df["Avg Loss"] = df["Loss"].rolling(window=window).mean()
        df["RS"] = df["Avg Gain"] / df["Avg Loss"]
        df["RSI"] = 100 - (100 / (1 + df["RS"]))
        return df

    def calculate_rsi_single(self, new_close, df, window=14):
        if len(df) >= window:  # Check if there are enough historical data points
            # Use the last 'window' number of data points for calculation
            last_window_data = df.iloc[-window:]
            change = new_close - last_window_data["Close"].iloc[-1]
            gain = max(0, change)
            loss = abs(min(0, change))
            avg_gain = (last_window_data["Avg Gain"].sum() + gain) / window
            avg_loss = (last_window_data["Avg Loss"].sum() + loss) / window
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
        df.at[len(df) - 1, "Change"] = change
        df.at[len(df) - 1, "Gain"] = gain
        df.at[len(df) - 1, "Loss"] = loss
        df.at[len(df) - 1, "Avg Gain"] = avg_gain
        df.at[len(df) - 1, "Avg Loss"] = avg_loss
        df.at[len(df) - 1, "RS"] = rs
        df.at[len(df) - 1, "RSI"] = rsi
        return rsi, df

    def calculate_bollinger_bands(self, df):
        window = 20
        df["MA"] = df["Close"].rolling(window=window).mean()
        df["STD"] = df["Close"].rolling(window=window).std()
        df["Upper Band"] = df["MA"] + (2 * df["STD"])
        df["Lower Band"] = df["MA"] - (2 * df["STD"])
        return df

    # increasing window size due to frequent calling and time difference being only 5 seconds
    def calculate_bollinger_bands_single(self, df, calls_to_single, window=20):
        calls_to_single = calls_to_single + 1
        window = window + calls_to_single
        if calls_to_single > 240:  # 5*240sec = 20min
            window = 240
        if len(df) >= window:  # Check if there are enough historical data points
            # Use the last 'window' number of data points for calculation
            last_window_data = df.iloc[-window:]
            ma = last_window_data["Close"].mean()
            std = last_window_data["Close"].std()
            upper_band = ma + (2 * std)
            lower_band = ma - (2 * std)
        else:
            # print('giving np.nan...')
            ma = np.nan
            std = np.nan
            upper_band = np.nan
            lower_band = np.nan
        df.at[len(df) - 1, "MA"] = ma
        df.at[len(df) - 1, "STD"] = std
        df.at[len(df) - 1, "Upper Band"] = upper_band
        df.at[len(df) - 1, "Lower Band"] = lower_band
        return ma, upper_band, lower_band, df, calls_to_single

    def buy_sell_print(self, dict_bs, ts, price, initial_price, logger):
        window_size = 5
        total_buy = 0
        total_sell = 0
        total_bq = 0
        total_sq = 0

        if price <= 50:
            rbq = 1000000  # 10 lac
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

        strength = 0

        for i in range(1, window_size + 1):
            # {'quantity': 4, 'price': 2963.55, 'orders': 3}
            total_buy = (
                total_buy + dict_bs["buy"][-i]["price"]
            )  # nifty doesn't have buy or sell data
            total_sell = total_sell + dict_bs["sell"][-i]["price"]
            total_bq = total_bq + dict_bs["buy"][-i]["quantity"]
            total_sq = total_sq + dict_bs["sell"][-i]["quantity"]
        avg_buy = total_buy / window_size
        avg_sell = total_sell / window_size
        rbq = 2000
        prcnt = 0.1  # 10%
        action = "hold"
        if (
            avg_buy > avg_sell and total_bq > total_sq and total_bq > rbq
        ):  # or (price > prcnt*initial_price):
            action = "buy"
            # # print('Buy!!!')
            string = "Buy!!!"
            strength = ((avg_buy - initial_price) / initial_price) * 100
            logger.critical(
                f"{ts}: "
                + string
                + f", avg buy: {avg_buy:.3f}, avg sell: {avg_sell:.3f}"
                + f", total bq: {total_bq}, total sq: {total_sq}"
                + f", strength: {strength}"
            )

        elif avg_buy < avg_sell and total_bq < total_sq and total_sq > rbq:
            # # print('Sell!!!')
            action = "sell"
            string = "Sell!!!"
            strength = ((avg_sell - initial_price) / initial_price) * 100
            logger.critical(
                f"{ts}: "
                + string
                + f", avg buy: {avg_buy:.3f}, avg sell: {avg_sell:.3f}"
                + f", total bq: {total_bq}, total sq: {total_sq}"
                + f", strength: {strength}"
            )

        else:
            # # print('Hold....')
            string = "Hold..."
            logger.info(
                f"{ts}: "
                + string
                + f", avg buy: {avg_buy:.3f}, avg sell: {avg_sell:.3f}"
                + f", total bq: {total_bq}, total sq: {total_sq}"
            )

        return action, avg_buy, avg_sell, total_bq, total_sq, rbq, strength


def buy(request):
    if request.method == "POST":
        stock_name = request.POST.get("stock_name")
        quantity = int(request.POST.get("quantity"))
        # print(quantity)
        current_price = float(request.POST.get("current_price"))
        extra_charges = current_price * quantity * 0.0015
        total = current_price * quantity + extra_charges

        # Update or create StockInventory entry
        stock_entry, created = StockInventory.objects.get_or_create(
            user=request.user,
            stock_name=stock_name,
        )
        if not created:
            stock_entry.quantity += quantity
        else:
            stock_entry.quantity = quantity
        stock_entry.save()

        # Create Trade entry
        trade = Trade.objects.create(
            user=request.user,
            stock_name=stock_name,
            quantity=quantity,
            buy_price=current_price,
            extra_charges=extra_charges,
            total=-total,
            is_buy=True,  # Indicate that this is a buy transaction
        )
        trade.save()
        return redirect("user_stocks")
    else:
        return render(request, "buy.html")


def sell(request):
    if request.method == "POST":
        stock_name = request.POST.get("stock_name")
        quantity = int(request.POST.get("quantity"))
        current_price = float(request.POST.get("current_price"))
        extra_charges = current_price * quantity * 0.0015
        total = current_price * quantity - extra_charges
        stock_inventory = StockInventory.objects.filter(
            user=request.user, stock_name=stock_name
        ).first()

        if stock_inventory:
            if stock_inventory.quantity >= quantity:
                stock_inventory.quantity -= quantity
                if stock_inventory.quantity == 0:
                    stock_inventory.delete()
                else:
                    trade = Trade.objects.create(
                        user=request.user,
                        stock_name=stock_name,
                        quantity=quantity,
                        sell_price=current_price,
                        extra_charges=extra_charges,
                        total=total,
                        is_buy=False,  # Indicate that this is a sell transaction
                    )
                    trade.save()
                    stock_inventory.save()
                return redirect("user_stocks")
            else:
                return render(
                    request, "sell.html", {"error": "Insufficient shares to sell."}
                )

        else:
            return render(
                request,
                "sell.html",
                {"error": "You do not own any shares of this stock."},
            )
    else:
        stock_name = request.GET.get(
            "stock_name"
        )  # Retrieve stock name from query parameters
        return render(request, "sell.html", {"stock_name": stock_name})


def user_stocks(request):
    # Retrieve the user's stocks
    user_stocks = StockInventory.objects.filter(user=request.user)

    # Get the username
    username = request.user.username
    return render(
        request, "user_stocks.html", {"user_stocks": user_stocks, "username": username}
    )


def trade_list(request):
    today = date.today()
    trades = Trade.objects.filter(user=request.user, trade_date=today)
    username = request.user.username
    total_sum = trades.aggregate(total_sum=Sum("total"))["total_sum"] or 0
    stock_summary = []
    stocks = set(trade.stock_name for trade in trades)

    for stock_name in stocks:
        bought_quantity = sum(
            trade.quantity
            for trade in trades
            if trade.stock_name == stock_name and trade.is_buy
        )
        sold_quantity = sum(
            trade.quantity
            for trade in trades
            if trade.stock_name == stock_name and not trade.is_buy
        )
        remaining_quantity = bought_quantity - sold_quantity
        if remaining_quantity > 0:
            stock_summary.append(
                {"stock_name": stock_name, "remaining_quantity": remaining_quantity}
            )
        # Retrieve stock summary data

    return render(
        request,
        "trade_list.html",
        {
            "trades": trades,
            "username": username,
            "total_sum": total_sum,
            "stock_summary": stock_summary,
        },
    )
