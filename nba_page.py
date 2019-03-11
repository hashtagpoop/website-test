from bs4 import BeautifulSoup
import requests
import re
import json
import pandas as pd
import datetime as dt
import sqlite3
from scipy.stats import norm 


conn = sqlite3.connect("daily_summary.db")
c = conn.cursor()

today = dt.date.today()
month = today.month
day = today.day - 1
year = today.year

#  this is for the df that has game scores
base_url = "https://www.basketball-reference.com"
winners = []
wscores = []
losers = []
lscores = []
links = []


#  this is for getting the actual game stats
scorer_names = []
scorer_pts = []
rebounder_names = []
rebounder_trb = []
assister_names = []
assister_ast = []

# url = "https://www.basketball-reference.com/boxscores/?month=4&day=11&year=2018"
url = "https://www.basketball-reference.com/boxscores/?month={}&day={}&year={}".format(month, day, year)


def get_games(url):

    sauce = requests.get(url)
    soup = BeautifulSoup(sauce.content, 'lxml')

    #  all of the games will be stored in here
    games = soup.find_all(class_="game_summary expanded nohover")

    for i in games:
        loser = i.find(class_="loser")
        loser_score = loser.find(class_="right").text
        loser_name = loser.find('a').text

        winner = i.find(class_="winner")
        winner_score = winner.find(class_="right").text
        winner_name = winner.find('a').text

        end_url = i.find(class_="gamelink").find('a').get('href')

        if int(winner_score) - int(loser_score) > 0:
            winners.append(winner_name)
            losers.append(loser_name)
            wscores.append(winner_score)
            lscores.append(loser_score)
            links.append(base_url+end_url)

        else:
            pass


def compose(links=None):
    if len(links) == 0:
        pass
    else:
        for link in links:
            tm1, tm2 = get_table(link)
            scoring(tm1)
            scoring(tm2)
            rebounding(tm1)
            rebounding(tm2)
            assisting(tm1)
            assisting(tm2)

    pts_df = pd.DataFrame({"Player": scorer_names, "PTS": scorer_pts})\
             .sort_values("PTS",ascending=False)[:5]
    trb_df = pd.DataFrame({"Player": rebounder_names, "TRB": rebounder_trb})\
             .sort_values("TRB",ascending=False)[:5]
    ast_df = pd.DataFrame({"Player": assister_names, "AST": assister_ast})\
             .sort_values("AST",ascending=False)[:5]

    pts_df.to_sql('pts', conn, if_exists='replace')
    trb_df.to_sql('trb', conn, if_exists='replace')
    ast_df.to_sql('ast', conn, if_exists='replace')


def get_table(url):
    try:
        # only takes the basic stats
        tm1 = pd.read_html(url, header=1)[0].iloc[:, :20].drop(5)
        tm1 = tm1.fillna(0)
        tm1 = tm1.apply(pd.to_numeric, errors='ignore')

        tm2 = pd.read_html(url, header=1)[2].iloc[:, :20].drop(5)
        tm2 = tm2.fillna(0)
        tm2 = tm2.apply(pd.to_numeric, errors='ignore')

        return tm1, tm2

    except Exception as e:
        print(e, "get_table")


def scoring(df):
    df = df[:-1]
    table = df.loc[(df["PTS"] > 15), ["Starters", "PTS"]]
    if table.empty:
        pass
    else:
        for i, v in table.values:
            scorer_names.append(i)
            scorer_pts.append(v)


def rebounding(df):
    df = df[:-1]
    table = df.loc[(df["TRB"] > 7), ["Starters", "TRB"]]
    if table.empty:
        pass
    else:
        for i, v in table.values:
            rebounder_names.append(i)
            rebounder_trb.append(v)


def assisting(df):
    df = df[:-1]
    table = df.loc[(df["AST"] > 6), ["Starters", "AST"]]
    if table.empty:
        pass
    else:
        for i, v in table.values:
            assister_names.append(i)
            assister_ast.append(v)


def grab_players():
    link = "https://www.basketball-reference.com/leagues/NBA_2019_per_game.html"
    sauce = requests.get(link)
    soup = BeautifulSoup(sauce.text, 'lxml')
    td = soup.find_all('td', attrs={'data-stat':'player'})
    names = [i.find('a').text for i in td]
    links = [i.find('a').get('href') for i in td]

    df = pd.DataFrame({'names':names, 'links':links})
    df = df.drop_duplicates()
    df["links"] = df["links"].str.extract(r"/(\w+.html)", expand=False)
    df.to_sql('links', conn, if_exists="replace")
    conn.commit()
    c.close()
    conn.close()


def grab_avg():
    cols_wanted = ["Pos", "PS/G", "TRB", "AST",  "FTA", "3P%", "FG%", "STL"]
    dfs = pd.read_html('https://www.basketball-reference.com/leagues/NBA_2019_per_game.html')
    df = dfs[0]
    df = df.drop_duplicates()
    df = df.set_index("Rk")
    df.drop("Rk", inplace=True)
    df = df[cols_wanted]
    df[cols_wanted[1:]] = df[cols_wanted[1:]].apply(pd.to_numeric)

    df.to_sql('average_table', conn, if_exists="replace")

    
# this is run every day
get_games(url)
grab_avg()
df = pd.DataFrame({"Win":winners,"WS":wscores,"Lose":losers,"LS":lscores})
df = df.apply(pd.to_numeric, errors="ignore")
df["diff"] = df.iloc[:, 1] - df.iloc[:, 3]
df = df.sort_values('diff', ascending=False)
df.to_sql('scores', conn, if_exists="replace")
# this is going to be the table that is maintained throughout the year
df.to_sql('games', conn, if_exists="append")
compose(links=links)
conn.commit()
c.close()
conn.close()

# this records in json file when we updated 
data = {"month": month, "day": day, "year": year}

with open("date.json", "w") as write_file:
    json.dump(data, write_file)


# if you are missing a days of data in the table
""" 
get_games(url of day)
df = pd.DataFrame({"Win":winners,"WS":wscores,"Lose":losers,"LS":lscores})
df = df.apply(pd.to_numeric, errors="ignore")
df["diff"] = df.iloc[:, 1] - df.iloc[:, 3]
df.to_sql('games', conn, if_exists="append")
"""
