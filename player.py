import pandas as pd
import re
from bs4 import BeautifulSoup
import requests
import datetime as dt
import sqlite3
from scipy.stats import norm
pd.options.mode.chained_assignment = None

cols_wanted = ["Date", "PTS", "TRB", "AST", "+/-", "FG", "FGA", "FTA", "3P", "3PA", "STL"]
year = (dt.datetime.now() + dt.timedelta(days=100)).year


def get_table(url):
    try:
        dfs = pd.read_html(url, index_col=0)
        original = dfs[7]
        original.drop("Rk", inplace=True)
        original.rename(columns={original.columns[4]: "Where"}, inplace=True)
        return original
    
    except Exception as e:
        print(e, "get_table")


def clean(original, cols):
    df = original[~original["G"].isna()][cols]
    try:
        df["Result"], df["By"] = original.iloc[:, 6].str.split(" ").str
    except:
        pass
    df["Result"] = df["Result"].astype('category')
    df = df.apply(pd.to_numeric, errors="ignore").fillna(0)

    # print(df)
    return df


def crossover(left, right):
    result = pd.merge(left, right, on= "Date")
    if len(result) == 0:
        print("No crossover between the two.")
    else:
        result = result.drop(['Result_y','By_y'], axis=1)
        return result


def position(link):
    sauce = requests.get(link)
    soup = BeautifulSoup(sauce.text, 'lxml')
    div = soup.find('div', attrs={'itemtype':"https://schema.org/Person"})
    positions = re.search(r"Position:\s+([\w ]+)\s", div.text).group(1)

    guard = "guard" in positions.lower()
    forward = "forward" in positions.lower()
    center = "center" in positions.lower()

    return [guard, forward, center]
        

def summarize(df, by="Result"):
    return df.groupby(by).size()


class Player:
    
    """ This will grab a players full name and use basketball-reference's url to retrieve a dataframe of 
    the players stats for a single season. Change the columns wanted to get more data.
    
    Parameters:
    _ _ _ _ _ _ 
    full_name = The full name of the player. Make sure you spell it correctly. 
    Only the first and last name will be necessary"""

    def __init__(self, full_name, time = None, url = None, data = None):
        self.f_name, self.l_name = full_name.split(' ')

        if data is None:
            self.url = url if url is not None else "https://www.basketball-reference.com/players/{}/{}{}01/gamelog/{}/"\
                .format(self.l_name[:1], self.l_name[:5], self.f_name[:2], time)
            
            try:
                self.df = clean(get_table(self.url), cols_wanted)
                
            except:
                print("If no tables found, make sure you spelled name correctly. It should be"
                      "the first and last name of the player with a space in between")

            try:
                self.positions = position(self.url)
            except Exception as e:
                print(e)
                
        else:
            self.df = clean(data, cols_wanted)

    def doubles(self):
        double_double = self.df.loc[(((self.df["PTS"] >= 10) & (self.df["AST"] >= 10)) |
           ((self.df["PTS"] >= 10) & (self.df["TRB"] >= 10)) |
           ((self.df["AST"] >= 10) & (self.df["TRB"] >= 10))) &
           ~((self.df["PTS"] >= 10) & (self.df["AST"] >= 10) & (self.df["TRB"] >= 10))]
 
        return double_double

    def triple_doubles(self):
        triple_double = self.df.loc[(self.df["PTS"] >= 10) & (self.df["AST"] >= 10) & (self.df["TRB"] >= 10)]

        return triple_double

    def ratio(self, df):
        loss, win = df.groupby("Result").size()
        total = (loss+win)
        return win/total
        
    def dubs(self):
        tds = len(self.triple_doubles())
        dds = len(self.doubles())
        summary_stats = []

        summary_stats.append("He has {} double doubles and {} triple doubles. \n".format(dds, tds))
        try:
            summary_stats.append("They are {0:.2f}% when he has a DD\n".format(self.ratio(self.doubles()) * 100))
        except:
            pass

        try:
            summary_stats.append("They are {0:.2f}% when he has a TD".format(self.ratio(self.triple_doubles())*100))
        except:
            pass

        return summary_stats

    def single(self, stat, num):
        single = self.df.loc[self.df[stat.upper()] > int(num)]
        return single

    def averages(self):
        pts = round(self.df["PTS"].mean(),2)
        trb = round(self.df["TRB"].mean(),2)
        ast = round(self.df["AST"].mean(),2)
        fta = round(self.df["FTA"].mean(),2)
        fgp = round(self.df["FG"].sum()/self.df["FGA"].sum(),2)
        threept = round(self.df["3P"].sum()/self.df["3PA"].sum(),2)
        stl = round(self.df["STL"].mean(),2)

        return [pts, trb, ast, fgp, fta, threept, stl]

    def ranking(self, avgs):
        conn = sqlite3.connect('daily_summary.db')
        df = pd.read_sql("SELECT * FROM average_table;", conn)

        # comment this out if you want to compare to league as a whole
        if self.positions[0] and self.positions[1]:
            df = df[df["Pos"].str.contains("F|G")]
            compared_position = "Guards and Forwards"
        elif self.positions[0]: # g, f, c
            df = df[df["Pos"].str.contains("G")]
            compared_position = "Guards"
        elif self.positions[1]:
            df = df[df["Pos"].str.contains("F")]
            compared_position = "Forwards"
        elif self.positions[2]:
            df = df[df["Pos"].str.contains("C")]
            compared_position = "Centers"
        else:
            compared_position = "players"

        pts = norm.cdf(avgs[0], df["PS/G"].describe()["mean"], df["PS/G"].describe()["std"])
        trb = norm.cdf(avgs[1], df["TRB"].describe()["mean"], df["TRB"].describe()["std"])
        ast = norm.cdf(avgs[2], df["AST"].describe()["mean"], df["AST"].describe()["std"])
        fgp = norm.cdf(avgs[3], df["FG%"].describe()["mean"], df["FG%"].describe()["std"])
        fta = norm.cdf(avgs[4], df["FTA"].describe()["mean"], df["FTA"].describe()["std"])
        threept = norm.cdf(avgs[5], df["3P%"].describe()["mean"], df["3P%"].describe()["std"])
        stl = norm.cdf(avgs[6], df["STL"].describe()["mean"], df["STL"].describe()["std"])

        stats = [pts, trb, ast, fgp, fta, threept, stl]
        grade = []

        for i in stats:
            if i > .95:
                grade.append("A+")
            elif i > .88:
                grade.append("A")
            elif i > .70:
                grade.append("B")
            elif i > .5:
                grade.append("C")
            else:
                grade.append("D")

        units = [3, 3, 3, 1, 2, 1, 2]
        total_attempted = sum(units)

        total_earned = 0

        try:
            for i in range(len(units)):
                if grade[i] == "A+":
                    total_earned += 4.0 * units[i]
                elif grade[i] == "A":
                    total_earned += 3.5 * units[i]
                elif grade[i] == "B":
                    total_earned += 3.0 * units[i]
                elif grade[i] == "C":
                    total_earned += 2.5 * units[i]
                else:
                    total_earned += 2.0 * units[i]
        except:
            total_earned = 0

        gpa = round(total_earned / total_attempted, 2)

        return grade, compared_position, gpa

    def totals(self):
        pts = sum(self.df.PTS)
        trb = sum(self.df.TRB)
        ast = sum(self.df.AST)
        three = sum(self.df["3P"])
        return pts, trb, ast, three

    def perform(self, crunch_time = "0:46:00"):
        sauce = requests.get(self.url)
        soup = BeautifulSoup(sauce.text, "lxml")

        h1 = soup.find_all('h1')
        full_name = re.search(r'^(\D+) \d', h1[0].text).groups()[0]
        f_name, *rest_name = full_name.split(" ")
        name = f"{f_name[:1]}. {' '.join(rest_name)}"

        tr = soup.find(class_="table_outer_container").find_all('tr')
        games = [i.find('a').get('href') for i in tr if 'boxscore' in str(i.find('a')) and
                 abs(int(i.find(attrs={'data-stat': 'game_result'}).get('csk'))) < 10]
        game_links = []

        attempted_ft = 0
        attempted_fg = 0
        made_ft = 0
        made_fg = 0

        layups_total = 0
        dunks_total = 0
        j_total = 0
        threes_total = 0
        below_5ft_total = 0
        mid_range_total = 0
        shots_total = 0

        for link in games:
            endlink = re.search(r'(\w+)\.', link).groups()[0]
            url = f"https://www.basketball-reference.com/boxscores/pbp/{endlink}.html"

            df = all_plays(url)

            layups, dunks, j, threes, below_5ft, mid_range, shots = shot_selection(df, name)
            layups_total += layups
            dunks_total += dunks
            j_total += j
            threes_total += threes
            below_5ft_total += below_5ft
            mid_range_total += mid_range
            shots_total += shots

            a, b, c, d, ot = quarters_perform(df)

            # add in test if ot exists
            if len(ot) > 1:
                att_ft, att_fg, m_ft, m_fg = crunch_stats(ot, name, crunch_time)
                if m_fg > 0:
                    print(url, m_fg)
                    game_links.append(url)
                
            else:
                att_ft, att_fg, m_ft, m_fg = crunch_stats(d, name, crunch_time)
                if m_fg > 0:
                    print(url, m_fg)
                    game_links.append(url)
                if att_fg > 0:
                    print(url, att_fg, "miss")
            # if m_fg > 0:
            #     print(url)

            attempted_ft += att_ft
            attempted_fg += att_fg
            made_ft += m_ft
            made_fg += m_fg

        if attempted_ft == 0 or attempted_fg == 0:
            summary = f"Free Throws: ({made_ft}/{attempted_ft}), Field Goals: ({made_fg}/{attempted_fg})"
        else:
            summary = f"FT: {round(made_ft/attempted_ft * 100,2)} % ({made_ft}/{attempted_ft}), "\
                f"FG: {round(made_fg/attempted_fg * 100,2)} % ({made_fg}/{attempted_fg})"

        td_dd = self.dubs()

        selection = [layups_total, dunks_total, j_total, threes_total]
        shot_breakdown = [below_5ft_total, mid_range_total]

        selection = [round(i/shots_total * 100, 2) for i in selection]
        shot_breakdown = [round(i/shots_total * 100, 2) for i in shot_breakdown]

        return summary, td_dd, game_links, selection, shot_breakdown


def quarters(df):
    # nonetype is not iterable
    try:
        q1, q2, q3, q4, *ot = df[df[1].str.contains("Start of")].index
    except:
        q1, q2, q3, q4, *ot = df[df[5].str.contains("Start of")].index

    quarter1 = df.loc[q1:q2 - 2]
    quarter2 = df.loc[q2:q3 - 2]
    quarter3 = df.loc[q3:q4 - 2]
    if ot:
        quarter4 = df.loc[q4:ot[0] - 2]
        ot = df.loc[ot[0]:]
    else:
        quarter4 = df.loc[q4:]

    return quarter1, quarter2, quarter3, quarter4, ot


def quarters_perform(df):
    q1, q2, q3, q4, *ot = df[df['time'].str.contains("Time")].index

    quarter1 = df.loc[q1 + 1:q2 - 1]
    quarter2 = df.loc[q2 + 1:q3 - 1]
    quarter3 = df.loc[q3 + 1:q4 - 1]
    if ot:
        quarter4 = df.loc[q4 + 1:ot[0] - 2]
        ot_index = df[df['pbp'].str.contains('overtime')].index[0]
        ot = df.loc[ot_index+2:]
    else:
        quarter4 = df.loc[q4 + 1:]

    return quarter1, quarter2, quarter3, quarter4, ot


def sum_box(play_list, team_name):
    play_list = play_list[1:]
    # print(team_name, "team_name")
    team_name = re.findall(r"(\w+)$", team_name)[0]

    try:
        play_list["Agent"] = play_list[1].str.extract(r"([A-Z]\. [\w\-]+)", expand=False)
        plays = 1
    except:
        play_list["Agent"] = play_list[5].str.extract(r"([A-Z]\. [\w\-]+)", expand=False)
        plays = 5

    # this is the issue that throws a 5 because ValueError not enough values to unpack
    q1, q2, q3, q4, ot = quarters(play_list)

    # notes is for crunch time and g_notes are the game notes
    notes = []
    g_notes = []
    looking_for = ["makes free throw", "makes 3-pt", "Turnover", "misses free throw", "Technical foul",
                   "Offensive Rebound"]

    if len(ot) > 1:
        ot[0] = ot[ot[0].str.contains(":\d\d")][0].apply(pd.to_datetime)
        quarter = ot
        crunch_time = quarter
    else:
        q4[0] = q4[q4[0].str.contains(":\d\d")][0].apply(pd.to_datetime)
        quarter = q4
        crunch_time = quarter[(quarter[0] < "5:00")]

    g_team = list(set(play_list["Agent"]))
    g_team_3pt = list(play_list[play_list[plays].str.contains(looking_for[1])]["Agent"])
    g_notes.extend([f"{i} ({team_name}) made {g_team_3pt.count(i)} 3 pt's" for i in g_team if g_team_3pt.count(i) > 4])
    g_team_tech = list(play_list[play_list[plays].str.contains(looking_for[4])]["Agent"])
    g_notes.extend([f"{i} ({team_name}) had {g_team_tech.count(i)} technicals" for i in g_team if g_team_tech.count(i) > 0])
    g_team_oboard = list(play_list[play_list[plays].str.contains(looking_for[4])]["Agent"])
    g_notes.extend([f"{i} ({team_name}) had {g_team_oboard.count(i)} offensive boards" for i in g_team if g_team_oboard.count(i) > 2])

    c_team = list(set(crunch_time["Agent"]))
    c_team_ft = list(crunch_time[crunch_time[plays].str.contains(looking_for[0])]["Agent"])
    notes.extend([f"{i} ({team_name}) made {c_team_ft.count(i)} ft's" for i in c_team if c_team_ft.count(i) > 3])

    c_team_mft = list(crunch_time[crunch_time[plays].str.contains(looking_for[3])]["Agent"])
    notes.extend([f"{i} ({team_name}) missed {c_team_mft.count(i)} ft's" for i in c_team if c_team_mft.count(i) > 1])

    c_team_3pt = list(crunch_time[crunch_time[plays].str.contains(looking_for[1])]["Agent"])
    notes.extend([f"{i} ({team_name}) made {c_team_3pt.count(i)} 3 pt's" for i in c_team if c_team_3pt.count(i) > 1])

    c_team_to = list(crunch_time[crunch_time[plays].str.contains(looking_for[2])]["Agent"])
    notes.extend([f"{i} ({team_name}) had {c_team_to.count(i)} TO's" for i in c_team if c_team_to.count(i) > 1])

    return g_notes, notes


def stats_table(url):
    try:
        # only takes the basic stats
        tm1 = pd.read_html(url, header=1)[0].iloc[:, :20].drop(5)
        tm2 = pd.read_html(url, header=1)[2].iloc[:, :20].drop(5)

        tm1 = tm1[:-1]
        tm2 = tm2[:-1]
        # 'MP', 'FG', 'FGA', 'FG%', '3P', '3PA', '3P%', 'FT', 'FTA', 'FT%', 'ORB',
        # 'DRB', 'TRB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS'],

        notes = []
        all_tm = tm1.append(tm2)
        all_tm = all_tm.set_index("Starters")
        all_tm = all_tm.fillna(0)
        all_tm = all_tm.apply(pd.to_numeric, errors="ignore")

        # the index of the values that we want
        pts_index = list(all_tm.columns).index("PTS")
        # end

        # dataframes that we are looking at
        over_pts = all_tm[all_tm["PTS"] > 22]
        # end

        for i in range(len(over_pts)):
            notes.extend([f"{over_pts.index[i]} scored {over_pts.iloc[i, pts_index]}"])

        return notes

    except Exception as e:
        print(e, "stats_table")


def crunch_stats(quarter4, name, crunch_time):
    df = quarter4

    try:
        # print(df.head())
        df['time'] = df['time'].apply(pd.to_datetime)
        df = df[df['time'] < crunch_time]

    except:
        try:
            df = df[3:]
            df['time'] = pd.to_datetime(df['time'], errors="coerce")
            # df['time'] = df['time'].apply(pd.to_datetime)
            df = df[df['time'] < crunch_time]
        except Exception as e:
            print(df.head())
            # print(df.tail())
            print(e)

    df["Agent"] = df['pbp'].str.extract(r"([A-Z]\. [\w\-]+)", expand=False)
    looking_for = ["makes free throw", "misses 3-pt", "makes 3-pt", "makes 2-pt", "misses 2-pt", "misses free throw"]

    # this is to make sure the dataframe composed of only actions by player
    df = df[df['Agent'] == name]

    made_fg = len(df[df['pbp'].str.contains(looking_for[2])]) + len(df[df['pbp'].str.contains(looking_for[3])])

    attempted_fg = len(df[df['pbp'].str.contains(looking_for[1])])
    attempted_fg += len(df[df['pbp'].str.contains(looking_for[4])])
    attempted_fg += made_fg

    made_ft = len(df[df['pbp'].str.contains(looking_for[0])])
    attempted_ft = made_ft + len(df[df['pbp'].str.contains(looking_for[5])])

    return attempted_ft, attempted_fg, made_ft, made_fg


def all_plays(link):
    ogs = pd.read_html(link)
    og = ogs[0].fillna("")

    og["pbp"] = og[1] + og[5]
    og = og[[0,'pbp']]
    og.columns = ['time', 'pbp']
    return og


def shot_selection(df, name):
    df["Agent"] = df['pbp'].str.extract(r"([A-Z]\. [\w\-]+)", expand=False)
    df["Dist"] = df['pbp'].str.extract(r"(\d+) ft", expand=False)
    looking_for = ["layup", "dunk", "2-pt \w+ shot", "3-pt jump shot"]
    df = df[df['Agent'] == name]
    df = df[df["pbp"].str.contains("makes|misses")]
    shots = df[df['pbp'].str.contains("shot|dunk|layup")]

    layups = len(df[df['pbp'].str.contains(looking_for[0])])
    dunks = len(df[df['pbp'].str.contains(looking_for[1])])
    j2 = len(df[df['pbp'].str.contains(looking_for[2])])
    threes = len(df[df['pbp'].str.contains(looking_for[3])])

    try:
        shots["Dist"] = pd.to_numeric(shots["Dist"])
        below = len(shots[shots['Dist'] <= 7])
        mid_range = len(shots[(shots['Dist'] <= 22) & (shots['Dist'] >= 8)])

    except Exception as e:
        print(e)
        print(df)
        below = None
        mid_range = None

    return layups, dunks, j2, threes, below, mid_range, len(shots)

