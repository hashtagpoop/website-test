import pandas as pd
import requests
pd.core.common.is_list_like = pd.api.types.is_list_like
import pandas_datareader.data as web
import datetime as dt


def stockBS(stock):

    url = 'https://finance.yahoo.com/quote/{}/balance-sheet?p={}'.format(stock, stock)

    dfs = pd.read_html(url, header=0, index_col=0)
    df = dfs[0]
    df = df.fillna('0').replace('-', 0)

    cols = df.columns
    df["CAGR"] = ((df[cols[0]].apply(pd.to_numeric) / df[cols[-1]].apply(pd.to_numeric)) ** (1 / len(cols)) - 1).apply(
        lambda x: "{0:.2%}".format(x))
    df["CAGR"] = df["CAGR"].str.replace("inf%|nan%", "-")

    df = clean(df)

    return df


def stockIS(stock):

    url = 'https://finance.yahoo.com/quote/{}/financials?p={}'.format(stock, stock)

    dfs = pd.read_html(url, header=0, index_col=0)
    df = dfs[0]
    df = df.fillna('0').replace('-', 0)

    cols = df.columns
    try:
        df["CAGR"] = ((df[cols[0]].apply(pd.to_numeric) / df[cols[-1]].apply(pd.to_numeric)) ** (1 / (len(cols)-1)) - 1).apply(
                        lambda x: "{0:.2%}".format(x))
        df["CAGR"] = df["CAGR"].str.replace("inf%|nan%", "-")
    except Exception as e:
        print(e)

    df = clean(df)

    return df


def tick(stock):

    end = dt.datetime.today()
    start = end - dt.timedelta(365)

    # endpoint = "https://www.alphavantage.co/query?"
    # params = {'function': 'TIME_SERIES_DAILY', 'symbol': stock, 'outputsize': 'full', 'apikey': "Q4BRRNRLKUIBMWQF "}
    # r = requests.get(endpoint, params)
    # ts = r.json()["Time Series (Daily)"]
    # x = [i for i in ts.keys()][:253]
    # _open = [float(ts[i]["1. open"]) for i in x]
    # high = [float(ts[i]["2. high"]) for i in x]
    # low = [float(ts[i]["3. low"]) for i in x]
    # close = [float(ts[i]["4. close"]) for i in x]
    # df = pd.DataFrame({"Date": x, "Open": _open, "High": high, "Low": low, "Close": close})
    # df = df.sort_values("Date")

    df = web.DataReader(stock, 'iex', start, end).reset_index()
    df.columns = ["Date", "Open", "High", "Low", "Close", "Volume"]

    # # this will create the rolling mean data of 20 and 50 days into another column
    df['EMA12'] = df["Close"].ewm(span=20, min_periods=0, adjust=False, ignore_na=False).mean()
    df['SMA50'] = df['Close'].rolling(window=50, center=False).mean()

    return df


def clean(df):
    def formats(x):
        x = "{0:,.0f}".format(x)
        if "-" in x:
            x = x.replace("-", "")
            return "({})".format(x)
        else:
            return x
    #
    # formats = lambda x: "{0:,.0f}".format(x)
    for col in df:
        if col == "CAGR":
            pass
        else:
            df[col] = df[col].astype(float).map(formats)
    return df






