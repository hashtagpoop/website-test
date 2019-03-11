from flask import Flask, render_template, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import pandas as pd
import json
import requests
import datetime as dt
from bs4 import BeautifulSoup
import sqlite3
import player
import fin
import plotly.graph_objs as go
from plotly.offline import plot
# from flask_caching import Cache


app = Flask(__name__)
limiter = Limiter(app, key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])
# cache = Cache(app, config={'CACHE_TYPE': 'simple'})
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', None)
today = dt.datetime.today()

#  this will be global functions


def table(df, class_=None):
    if class_ is None:
        df_html = "<table class='w3-table df-obj' style=''>"
    else:
        df_html = f"<table class='w3-table df-obj {class_}' style=''>"

    df_html += "<thead><tr><th style=''></th>"
    for i in range(len(df.columns)):
        df_html += "<th>{}</th>".format(df.columns[i])
    df_html += "</tr></thead>"
    df_html += "<tbody>"
    for i in range(len(df)):
        df_html += "<tr>"
        df_html += "<td>{}</td>".format(df.index[i])
        for co in range(len(df.columns)):
            # try:
            #     if df.iloc[i, co].contains("("):
            #         df_html += "<td style='text-align:right;color:red;'>{}</td>".format(df.iloc[i, co])
            #     else:
            #         df_html += "<td style='text-align:right'>{}</td>".format(df.iloc[i, co])
            # except:
                df_html += "<td style='text-align:right;height:10px;'>{}</td>".format(df.iloc[i, co])
        df_html += "</tr>"
    df_html += "</tbody>"
    df_html += "</table>"
    return df_html


# this is used when someone hits a "individual matchup" request
def all_plays(link):
    url = link[:47] + "pbp/" + link[47:]
    og = pd.read_html(url)
    og = og[0].fillna("")

    if og[1].head().str.contains("Start").any():
        pass
    else:
        og.iloc[2, 1] = "Start of Quarter"

    og[5][og[1].str.contains("Start of")] = "Start of Quarter"
    og[5][og[1].str.contains("End of")] = "End of Quarter"
    tm1 = og[og[1] != ""].drop([3, 4, 5], axis="columns")
    tm2 = og[og[5] != ""].drop([1, 2, 3], axis="columns")
    return tm1, tm2


def plays(df, search_item=""):
    try:
        play_list = df[df[1].str.contains(search_item)]
    except:
        play_list = df[df[5].str.contains(search_item)]

    return play_list


def quarter_sum(play_list):
    q1, q2, q3, q4, ot = player.quarters(play_list)
    summary = []
    count = 1

    for quarter in [q1, q2, q3, q4, ot]:
        try:
            if count < 5:
                summary.append("""<p style="text-align:center;">----- <b>Quarter {}</b> -----</p>
                            <ul class="w3-ul">
                                <li>Num of Assists: {}</li>
                                <li>Num of Made 3's:    {}</li>
                                <li>Num of Missed 3's:  {}</li>
                                <li>Num of Turnovers:   {}</li>
                                <li>Num of FTA:      {}</li>
                            </ul>
                        """.format(count, len(plays(quarter, "assist")), len(plays(quarter, "makes 3-pt")),
                                   len(plays(quarter, "misses 3-pt")), len(plays(quarter, "Turnover")),
                                   len(plays(quarter, "free throw"))))

                count += 1
            else:
                summary.append("""<p style="text-align:center;">----- <b>Overtime</b> -----</p>
                                        <ul class="w3-ul">
                                            <li>Num of Assists: {}</li>
                                            <li>Num of Made 3's:    {}</li>
                                            <li>Num of Missed 3's:  {}</li>
                                            <li>Num of Turnovers:   {}</li>
                                            <li>Num of FTA:      {}</li>
                                        </ul>
                                    """.format(len(plays(quarter, "assist")), len(plays(quarter, "makes 3-pt")),
                                               len(plays(quarter, "misses 3-pt")), len(plays(quarter, "Turnover")),
                                               len(plays(quarter, "free throw"))))
        except:
            pass

    return summary
# end of global functions


@app.route("/", methods=["GET", "POST"])
@limiter.exempt
def hello():

    return render_template('flaskgpa.html')


@app.route("/calc/", methods=["POST"])
@limiter.exempt
def calc():
    if request.method == "POST":

        try:

            units = [val for key, val in request.form.items() if "unit" in key]
            units = [int(unit) for unit in units if unit != ""]
            # unit1 = int(request.form.get('unit1') or 0)
            # units = [unit1, unit2, unit3, unit4, unit5, unit6, unit7]

            total_attempted = sum(units)

            grades = [val for key, val in request.form.items() if "grade" in key]
            grades = [grade.upper() for grade in grades if grade != ""]

            total_earned = 0

            if len(units) == 0:
                gpa = 0
            else:
                try:
                    for i in range(len(units)):
                        if grades[i] == "A" or grades[i] == "A+":
                            total_earned += 4.0 * units[i]
                        elif grades[i] == "A-":
                            total_earned += 3.7 * units[i]
                        elif grades[i] == "B+":
                            total_earned += 3.3 * units[i]
                        elif grades[i] == "B":
                            total_earned += 3.0 * units[i]
                        elif grades[i] == "B-":
                            total_earned += 2.7 * units[i]
                        elif grades[i] == "C+":
                            total_earned += 2.3 * units[i]
                        elif grades[i] == "C":
                            total_earned += 2.0 * units[i]
                        elif grades[i] == "C-":
                            total_earned += 1.7 * units[i]
                        elif grades[i] == "D+":
                            total_earned += 1.3 * units[i]
                        elif grades[i] == "D":
                            total_earned += 1.0 * units[i]
                        elif grades[i] == "D-":
                            total_earned += 0.7 * units[i]
                        elif grades[i] == "F+":
                            total_earned += 0.3 * units[i]
                        else:
                            total_earned += 0 * units[i]
                except:
                    total_earned = 0

                gpa = round(total_earned/total_attempted, 2)

            return jsonify(gpa=gpa)  # this is so that the jquery can use the json data

        except Exception as e:
            gpa = "error"

            return jsonify(gpa=gpa)


@app.route("/nba/", methods=["GET"])
def nba():
    module_dir = os.path.dirname(__file__)
    
    conn = sqlite3.connect('daily_summary.db')

    pts = pd.read_sql("SELECT * FROM pts;", conn).drop('index', axis=1)
    trb = pd.read_sql("SELECT * FROM trb;", conn).drop('index', axis=1)
    ast = pd.read_sql("SELECT * FROM ast;", conn).drop('index', axis=1)
    scores = pd.read_sql("SELECT * FROM scores;", conn).drop('index', axis=1)
    scores.columns = ["Winner", "", "Loser", " ", "diff"]
    scores = scores.drop('diff', axis=1)

    if pts.empty:
        with open(module_dir+"/date.json", "rb") as read:
            data = json.load(read)
        date = "{} - {} - {}".format(data["month"], data["day"], data["year"])
        announcement = "Sorry, there are no games today."
        return render_template('nba.html', date=date, announcement=announcement)

    else:
        with open(module_dir+"/date.json", "rb") as read:
            data = json.load(read)

        date = "{} - {} - {}".format(data["month"], data["day"], data["year"])

        return render_template('nba.html', pts=pts.to_html(classes="w3-table w3-centered df-obj", index=False),
                               ast=ast.to_html(classes="w3-table w3-centered df-obj", index=False),
                               trb=trb.to_html(classes="w3-table w3-centered df-obj", index=False),
                               scores=scores.to_html(classes="w3-table w3-centered df-obj", index=False),
                               date=date)


@app.route("/matchup/", defaults={'year': (dt.datetime.today() - dt.timedelta(days=1)).year,
                                  'month': (dt.datetime.today() - dt.timedelta(days=1)).month,
                                  'day': (dt.datetime.today() - dt.timedelta(days=1)).day}, methods=["GET", "POST"])
@app.route("/matchup/<year>/<month>/<day>", methods=["GET", "POST"])
def team_matchup(year, month, day):
    base_url = "https://www.basketball-reference.com"
    winners = []
    wscores = []
    losers = []
    lscores = []
    links = []

    y_date = dt.date(year=int(year), month=int(month), day=int(day)) - dt.timedelta(days=1)
    t_date = dt.date(year=int(year), month=int(month), day=int(day)) + dt.timedelta(days=1)

    def get_games(url):
        sauce = requests.get(url)
        soup = BeautifulSoup(sauce.content, 'lxml')
        games = soup.find_all(class_="game_summary expanded nohover")

        for i in games:
            loser = i.find(class_="loser")
            loser_score = loser.find(class_="right").text
            loser_name = loser.find('a').text

            winner = i.find(class_="winner")
            winner_score = winner.find(class_="right").text
            winner_name = winner.find('a').text

            end_url = i.find(class_="gamelink").find('a').get('href')

            winners.append(winner_name)
            losers.append(loser_name)
            wscores.append(winner_score)
            lscores.append(loser_score)
            links.append(base_url + end_url)

    get_games("https://www.basketball-reference.com/boxscores/?month={}&day={}&year={}"
              .format(month, day, year))

    short_links = [link.replace("https://www.basketball-reference.com/boxscores/", "") for link in links]
    routable_url = ["/quarter/" + link for link in short_links]
    zipper = zip(winners, losers, routable_url)

    date_of_games = f"{month}-{day}-{year}"

    if len(links) > 0:
        return render_template('matchup.html', zip=zipper, date_of_games=date_of_games, day=int(day), year=year,
                               month=month, y_date=y_date, t_date=t_date)
    else:
        announcement = "Sorry, no games on {}/{}".format(month, day)
        recommendation = "<a href='/matchup/2018/04/06'>Click here to see 2018/04/06</a>"
        # return redirect(url_for("team_matchup", year=2018, month=4, day=6))
        return render_template('matchup.html', announcement=announcement, recommendation=recommendation,
                               day=int(day), month=month, year=year, y_date=y_date, t_date=t_date)


@app.route("/quarter/", defaults={"link": ""}, methods=["GET", "POST"])
@app.route("/quarter/<link>", methods=["GET", "POST"])
def matchup(link):
    if link != "":
        pass
    else:
        if len(request.form["gm_url"]) > 5:
            link = request.form["gm_url"]
        else:
            link = "201806080CLE.html"
    base = "https://www.basketball-reference.com/boxscores/" + link

    try:
        team1, team2 = all_plays(base)
        away_team = quarter_sum(team1)
        home_team = quarter_sum(team2)

        crunch_time = "Crunch Time - 5 mins left" if len(away_team) <= 4 else "Overtime"

        tm1_ast = len(plays(team1, "assist"))
        tm1_3made = len(plays(team1, "makes 3-pt"))
        tm1_3missed = len(plays(team1, "misses 3-pt"))
        tm1_turnover = len(plays(team1, "Turnover"))
        tm1_fta = len(plays(team1, "free throw"))

        tm2_ast = len(plays(team2, "assist"))
        tm2_3made = len(plays(team2, "makes 3-pt"))
        tm2_3missed = len(plays(team2, "misses 3-pt"))
        tm2_turnover = len(plays(team2, "Turnover"))
        tm2_fta = len(plays(team2, "free throw"))

        sauce = requests.get(base)
        soup = BeautifulSoup(sauce.content, 'lxml')
        scorebox_tag = soup.find(class_='scorebox')
        strong_tag = scorebox_tag.find_all('strong')
        away_name, home_name = [i.find('a').text for i in strong_tag]
        scores = scorebox_tag.find_all(class_="score")
        away_score, home_score = [i.text for i in scores]

        # print(away_name, home_name)

        config = {'showLink': False, "displayModeBar": False}
        y = ["Assists", "Made 3's", "Missed 3's", "Turnovers", "FTA's"]
        x1 = [tm1_ast, tm1_3made, tm1_3missed, tm1_turnover, tm1_fta]
        x2 = [tm2_ast, tm2_3made, tm2_3missed, tm2_turnover, tm2_fta]

        trace1 = {"x": x1,
                  "y": y,
                  "marker": {"color": "pink", "size": 18}, "hoverinfo": "x",
                  "mode": "markers", "name": away_name, "type": "scatter"}

        trace2 = {"x": x2,
                  "y": y,
                  "marker": {"color": "blue", "size": 18}, "hoverinfo": "x",
                  "mode": "markers", "name": home_name, "type": "scatter"}

        data = [trace1, trace2]
        layout = go.Layout(autosize=True,
                           plot_bgcolor='rgba(0,0,0,0)',
                           paper_bgcolor='rgba(0,0,0,0)',
                           showlegend=True,
                           margin=dict(t=55, l=100, b=30, r=10),
                           legend=dict(orientation="h"), xaxis=dict(showline=True),
                           title=f"{away_name} vs {home_name}", hovermode='closest')

        fig = go.Figure(data=data, layout=layout)
        dotchart = plot(fig, output_type="div", config=config)

        c_notes = []
        g_notes = []
        # print(away_name, "away")
        # print(home_name, "home")
        tm1_game, tm1_crunch = player.sum_box(team1, away_name)
        tm2_game, tm2_crunch = player.sum_box(team2, home_name)
        c_notes.extend(tm1_crunch)
        g_notes.extend(tm1_game)
        c_notes.extend(tm2_crunch)
        g_notes.extend(tm2_game)

        if player.stats_table(base) is None:
            pass
        else:
            g_notes.extend(player.stats_table(base))

        return render_template('individual.html', away=away_team, home=home_team, away_name=away_name,
                               home_name=home_name, away_score=away_score, home_score=home_score, dotchart=dotchart,
                               g_notes=g_notes, c_notes=c_notes, crunch_time=crunch_time, base=base)
    except Exception as e:
        error = "Sorry, this game was too recent and the play-by-play list has not been released yet. Generally" \
                " speaking, the pbp list is uploaded a day after the game."
        print(e)

        return render_template("individual.html", error=error)


@app.route("/player/", defaults={'year': (dt.datetime.today()+dt.timedelta(days=100)).year,
                                 'minute': "0", 'sec': "46"}, methods=["GET", "POST"])
@app.route("/player/<year>/<minute>/<sec>", methods=["GET", "POST"])
def player_stats(year, minute, sec):
    conn = sqlite3.connect('daily_summary.db')
    c = conn.cursor()

    c.execute("SELECT * FROM links;")
    rows = c.fetchall()

    names = [row[1] for row in rows]
    links = [row[2] for row in rows]

    if request.method == "GET":
        # player1 = player.Player("Josh Hart", time=2019)
        # player1_avg = player1.averages()

        return render_template("player.html", names=names)
    else:
        name = request.form["chose"]
        index_name = name.lower()
        year = year
        time = f"{minute}:{sec}:00"
        try:
            lower_names = [name.lower() for name in names]
            if index_name in lower_names:
                uni_link = links[lower_names.index(index_name)].replace(".html", "")
                url = f"https://www.basketball-reference.com/players/{uni_link[0]}/{uni_link}/gamelog/{year}/"
                person = player.Player(full_name=name, url=url)
            else:
                person = player.Player(full_name=name, time=year)
                url = person.url

            avg = person.averages()
            name = name.split(" ")
            name = [i.capitalize() for i in name]
            name = " ".join(name)
            ranks, compared_to, gpa = person.ranking(avg)

            # selection is layups, dunks, jump shots, and threes
            # shot_breakdown is below 5 ft and mid range selection
            summary, td_dd, game_links, selection, shot_breakdown = person.perform(time)
            summary = summary.split(", ")

            config = {'showLink': False, "displayModeBar": False}
            colors = ['#dbe9d8', '#fae596', '#3fb0ac', '#729f98']

            labels = ["Layups", "Dunks", "Jump Shots", "Threes"]
            values = selection

            pie_trace = go.Pie(labels=labels, values=values,
                               hoverinfo='percent', textinfo='label',
                               textfont=dict(size=20), hole=.65, pull=[.03, .03, .03, .03], textposition="auto",
                               marker=dict(colors=colors, line=dict(color='#000000', width=1)))

            layout = go.Layout(autosize=True,
                               plot_bgcolor='rgba(0,0,0,0)',
                               paper_bgcolor='rgba(0,0,0,0)',
                               showlegend=True,
                               margin=dict(t=65, l=35, b=50, r=20),
                               legend=dict(orientation="h"))

            fig = go.Figure(data=[pie_trace], layout=layout)
            html_pie = plot(fig, output_type='div', config=config)

            return render_template("player.html", names=names, person=name, avg=avg, year=year, summary=summary,
                                   url=url, td_dd=td_dd, ranks=ranks, compared_to=compared_to, grade_point=gpa,
                                   game_links=game_links, selection=selection, shot_breakdown=shot_breakdown,
                                   html_pie=html_pie)

        except Exception as e:
            error = "Player was not found. Please try again."
            print(e)

            return render_template("player.html", names=names, error=error)


@app.route('/fin/', methods=["GET", "POST"])
def fin_page():

    # make this into a blank page
    if request.method == "GET":
        config = {'showLink': False, "displayModeBar": False}
        api = "Q4BRRNRLKUIBMWQF"
        try:
            begin = dt.datetime.now()

            endpoint = "https://www.alphavantage.co/query?"
            params = {'function': 'SECTOR', 'apikey': api}
            r = requests.get(endpoint, params)
            sector = r.json()["Rank C: 5 Day Performance"]
            x = [sector_name for sector_name in sector.keys()]
            y = [sector[sector_name].replace("%", "") for sector_name in x]
            trace0 = go.Bar(
                x=x,
                y=y,
                text=['{:.1%}'.format(float(num) / 100) for num in y],
                hoverinfo='text',
                name="5 Day",
                marker=dict(
                    color='rgb(158,202,225)',
                    line=dict(
                        color='rgb(8,48,107)',
                        width=1.0,
                    )
                ),
                opacity=0.6
            )

            sector_3mo = r.json()["Rank E: 3 Month Performance"]
            x3mo = [sector_name for sector_name in sector_3mo.keys()]
            y3mo = [sector_3mo[sector_name].replace("%", "") for sector_name in x3mo]

            trace1 = go.Bar(
                x=x3mo,
                y=y3mo,
                text=['{:.1%}'.format(float(num) / 100) for num in y3mo],
                hoverinfo='text',
                name="3 Month",
                marker=dict(
                    color='rgb(55, 83, 109)',
                    line=dict(
                        color='rgb(55, 83, 109)',
                        width=1.0,
                    )
                ),
                opacity=0.6
            )

            data = [trace0, trace1]

            head = "Sector Performance"

            layout = go.Layout(autosize=True, height=600,
                               plot_bgcolor='rgba(0,0,0,0)',
                               paper_bgcolor='rgba(0,0,0,0)',
                               margin=dict(t=50, l=30, b=100, r=0),
                               legend=dict(orientation="h", x=0, y=1.2),
                               barmode='group',
                               bargap=0.15,
                               bargroupgap=0.1
                               )

            fig = go.Figure(data=data, layout=layout)
            html_get = plot(fig, output_type='div', config=config)
            print(dt.datetime.now() - begin)

        except:
            html_get = "Error"
            head = "Sorry"

        return render_template('fin.html', html_get=html_get, head=head)

    else:
        api = "Q4BRRNRLKUIBMWQF"
        # configurations where we hide the Plotly link and the toggle buttons
        config = {'showLink': False, "displayModeBar": False}

        try:
            begin = dt.datetime.now()
            stock = request.form.get("input_ticker").strip().upper()
            df = fin.tick(stock)

            params_rsi = {'function': 'rsi', 'symbol': stock, 'interval': 'daily', 'time_period': '14',
                          'series_type': 'close', 'datatype': 'json', 'apikey': api}

            params_bands = dict(function="BBANDS", symbol=stock, interval="weekly", time_period=12,
                                series_type="close", matype="1", nbdevup=2, nbdevdn=2, apikey=api)

            params_macd = dict(function="MACD", symbol=stock, interval="daily", series_type="close", apikey=api)

            params_adx = dict(function="ADX", symbol=stock, interval="daily", time_period=20, apikey=api)

            # requesting the data from alphavantage
            endpoint = "https://www.alphavantage.co/query?"
            r = requests.get(endpoint, params_rsi)
            rsi = r.json()["Technical Analysis: RSI"]
            x = [i for i in rsi.keys()][:150]
            y = [rsi[i]["RSI"] for i in x][:150]

            r = requests.get(endpoint, params_bands)
            bands = r.json()["Technical Analysis: BBANDS"]
            bands_x = [i for i in bands.keys()][:53]
            bands_upper = [bands[i]["Real Upper Band"] for i in bands_x]
            bands_lower = [bands[i]["Real Lower Band"] for i in bands_x]
            bands_middle = [bands[i]["Real Middle Band"] for i in bands_x]

            r = requests.get(endpoint, params_macd)
            macd = r.json()["Technical Analysis: MACD"]
            macd_x = [i for i in macd.keys()][:250]
            macd_signal = [macd[i]["MACD_Signal"] for i in macd_x]
            macd_line = [macd[i]["MACD"] for i in macd_x]

            r = requests.get(endpoint, params_adx)
            adx = r.json()["Technical Analysis: ADX"]
            adx_x = [i for i in adx.keys()][:250]
            adx_score = [adx[i]["ADX"] for i in adx_x]
            # end

            trace = go.Candlestick(x=df.Date,
                                   open=df.Open,
                                   high=df.High,
                                   low=df.Low,
                                   close=df.Close,
                                   name=stock, increasing=dict(line=dict(color='#17BECF')),
                                   decreasing=dict(line=dict(color='#7F7F7F')))

            ema20 = go.Scatter(x=df.Date,
                               y=df["EMA12"],
                               name="EMA12",
                               mode="lines",
                               line={"color": "yellow"})

            sma50 = go.Scatter(x=df.Date,
                               y=df["SMA50"],
                               name="SMA50",
                               mode="lines",
                               line={"color": "blue"})

            signal = go.Scatter(x=macd_x,
                                y=macd_signal,
                                name="Signal",
                                mode="lines",
                                line={"color": "#80BD9E"})

            macd_scatter = go.Scatter(x=macd_x,
                                      y=macd_line,
                                      name="MACD",
                                      mode="lines",
                                      line={"color": "#F98866"})

            upper_band = go.Scatter(x=bands_x, y=bands_upper, name="Upper", mode="lines", line={"color": "#F98866"})
            lower_band = go.Scatter(x=bands_x, y=bands_lower, name="Lower", mode="lines", line={"color": "#F98866"})
            middle_band = go.Scatter(x=bands_x, y=bands_middle, name="EMA 12", mode="lines", line={"color": "#80BD9E"})

            # layout for the fin start page
            layout = go.Layout(autosize=True,  # width=825, height=550,
                               plot_bgcolor='rgba(0,0,0,0)',
                               paper_bgcolor='rgba(0,0,0,0)',
                               margin=dict(t=10, l=50, b=5, r=25),
                               legend=dict(orientation="h", x=0, y=1.2),
                               xaxis=dict(
                                   rangeselector=dict(
                                       buttons=list([
                                           dict(count=1, label='1m', step='month', stepmode='backward'),
                                           dict(count=3, label='3m', step='month', stepmode='backward'),
                                           dict(count=6, label='6m', step='month', stepmode='backward'),
                                           dict(count=1, label='YTD', step='year', stepmode='todate'),
                                           dict(count=1, label='1y', step='year', stepmode='backward')
                                       ])
                                   )))

            # layout for the rsi
            rlayout = go.Layout(autosize=True,  # width=425, height=250,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)',
                                showlegend=False,
                                margin=dict(t=65, l=35, b=50, r=20),
                                title="<a href='https://www.investopedia.com/terms/r/rsi.asp'>RSI</a>")

            # layout for the adx
            adx_layout = go.Layout(autosize=True,  # width=425, height=250,
                                   plot_bgcolor='rgba(0,0,0,0)',
                                   paper_bgcolor='rgba(0,0,0,0)',
                                   showlegend=True,
                                   margin=dict(t=65, l=35, b=50, r=20),
                                   title="<a href='https://tradingmarkets.com/recent/direction_is_the_key_to_using_"
                                         "adx_correctly-639297.html'>ADX (20)</a>",
                                   legend=dict(orientation="h"))

            # layout for the bollinger bands
            blayout = go.Layout(autosize=True,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)',
                                showlegend=True,
                                margin=dict(t=65, l=35, b=50, r=20),
                                legend=dict(orientation="h"),
                                title="<a href='https://www.investopedia.com/trading/using-bollinger-"
                                      "bands-to-gauge-trends/'>Bollinger Bands (12)</a>")

            # layout for the macd
            mlayout = go.Layout(autosize=True,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)',
                                showlegend=True,
                                margin=dict(t=65, l=35, b=50, r=20),
                                legend=dict(orientation="h"),
                                title="<a href='https://www.tradeciety.com/tips-how-to-use-the-macd/'>MACD</a>")

            # these two are for the RSI only
            rsi_trace = go.Scatter(x=x, y=y, name="RSI", line={"color": "black"})
            upper_rsi = go.Scatter(x=x, y=[70 for i in x], mode="lines",
                                   hoverinfo='none', fill="tonexty",
                                   line={"color": "blue", "dash": "dash"})
            # end

            # these are for the ADX
            strong_trend = go.Scatter(x=adx_x, y=[25 for i in adx_x], name="Strong Trend", mode="lines",
                                      hoverinfo='none',
                                      line={"color": "blue", "dash": "dash"})

            no_trend = go.Scatter(x=adx_x, y=[20 for i in adx_x], mode="lines", name="No Trend",
                                  hoverinfo='none',
                                  line={"color": "#80BD9E", "dash": "dash"})

            adx_scatter = go.Scatter(x=adx_x,
                                     y=adx_score,
                                     name="ADX",
                                     mode="lines",
                                     line={"color": "#375E97"})
            # end

            # figures for all the plots
            fig_rsi = go.Figure([rsi_trace, upper_rsi], layout=rlayout)
            fig_adx = go.Figure([strong_trend, no_trend, adx_scatter], layout=adx_layout)
            fig_bands = go.Figure([upper_band, lower_band, middle_band], layout=blayout)
            fig = go.Figure([trace, ema20, sma50], layout=layout)
            fig_macd = go.Figure([signal, macd_scatter], layout=mlayout)
            # end

            # this is where all the plotting happens
            ts = plot(fig, output_type='div', config=config)
            html_rsi = plot(fig_rsi, output_type='div', config=config)
            html_bands = plot(fig_bands, output_type="div", config=config)
            html_macd = plot(fig_macd, output_type='div', config=config)
            html_adx = plot(fig_adx, output_type='div', config=config)
            # end

            print(dt.datetime.now() - begin)

            return render_template('fin.html', stock=stock.upper(), ts=ts, rsi=html_rsi, html_bands=html_bands,
                                   html_macd=html_macd, html_adx=html_adx)

        except Exception as e:
            print(e)
            return render_template('fin.html', error="Encountered an error, please double check. If making multiple"
                                                     "requests, please allow time in between requests.")


@app.route('/financial_statements/', methods=["POST"])
def fs():
    stock = request.form["stock"].strip().upper()
    df = fin.tick(stock)

    # configurations where we hide the Plotly link and the toggle buttons
    config = {'showLink': False, "displayModeBar": False}

    # all of the magic for the balance sheet and income statement
    bs = fin.stockBS(stock)
    _is = fin.stockIS(stock)
    bs = bs[(bs.iloc[:, 0] != "0")]
    _is = _is[(_is.iloc[:, 0] != "0")]
    _is = _is.drop("CAGR", axis=1)
    bs_html = table(bs)
    is_html = table(_is)

    # this is for the 52 week period stats
    s_low = round(df.Low.min(), 2)
    s_high = round(df.High.max(), 2)
    _return = '{:.1%}'.format((df.Close.iloc[-1] - df.Open.iloc[0])/df.Open.iloc[0])
    # end

    try:
        pie = go.Pie(labels=["Total Current Assets", "Total Current Liabilities"],
                     values=[bs.loc["Total Current Assets"][0].replace(",", ""),
                             bs.loc["Total Current Liabilities"][0].replace(",", "")],
                     marker=dict(colors=["#9068be", "#6ed3cf"]),
                     hole=.5, hoverinfo="value", textposition="outside"
                                                              "")
        playout = go.Layout(autosize=True,  # width=425, height=300,
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            margin=dict(t=65, l=25, b=0, r=0),
                            title="<a href='https://www.investopedia.com/terms"
                                  "/c/currentratio.asp'>Current Ratio</a>",
                            legend=dict(orientation="h"))

        fig2 = go.Figure(data=[pie], layout=playout)
        pie = plot(fig2, output_type='div', config=config)
    except:
        error = "Wow, this is either a young company you are looking into or they are missing some information " \
                "on their financials. " \
                "Sorry, please try again not been released yet. <a target='_blank' " \
                "href='https://finance.yahoo.com/quote/" \
                f"{stock}/financials?p={stock}'>" \
                "Click here</a> for their financials."

        return jsonify(error=error)

    exp = go.Bar(
        y=[i for i in _is.columns],
        x=[_is.iloc[1, i] for i in range(len(_is.columns))],
        name='Cost of Revenue', hoverinfo='x',
        orientation='h',
        marker=dict(
            color='rgba(246, 78, 139, 0.6)',
            line=dict(
                color='rgba(246, 78, 139, 1.0)',
                width=3)
        )
    )
    rev = go.Bar(
        y=[i for i in _is.columns],
        x=[_is.iloc[0, i] for i in range(len(_is.columns))],
        name='Revenue', hoverinfo='x',
        orientation='h',
        marker=dict(
            color='rgba(58, 71, 80, 0.6)',
            line=dict(
                color='rgba(58, 71, 80, 1.0)',
                width=3)
        )
    )
    gross_p = [exp, rev]
    # layout for gross profit
    glayout = go.Layout(autosize=True, barmode='group',
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        showlegend=True,
                        margin=dict(t=65, l=75, b=50, r=10),
                        legend=dict(orientation="h"),
                        title="Gross Profit")
    fig_profit = go.Figure(gross_p, layout=glayout)
    html_profits = plot(fig_profit, output_type="div", config=config)
    # end
    return jsonify(bs=bs_html, is_html=is_html, pie=pie, s_low=s_low,
                   s_high=s_high, _return=_return, html_profits=html_profits, error=False)


@app.route('/boxscores/<where>/', methods=["POST"])
def boxscores(where):
    base = request.form["base"]
    print(base)
    sauce = requests.get(base)
    soup = BeautifulSoup(sauce.text, 'lxml')
    tables = soup.find_all('table')

    cols = ['MP', 'PTS', 'AST', 'TRB', 'FG', 'FGA', '3P', '3PA', '3P%', 'FT', 'FTA',
            'ORB', 'STL', 'BLK', 'TOV', 'PF', '+/-']

    df = pd.read_html(str(tables[0]), header=1, index_col=0)[0]
    df = df.fillna("-")

    df1 = pd.read_html(str(tables[2]), header=1, index_col=0)[0]
    df1 = df1.fillna("-")

    df.MP = df.MP.str.replace("Did Not Play|Did Not Dress", "DNP")
    df1.MP = df1.MP.str.replace("Did Not Play|Did Not Dress", "DNP")

    df = df.drop("Reserves")[cols]
    df1 = df1.drop("Reserves")[cols]

    if where == "home":
        return jsonify(boxscore2=table(df1, "w3-striped lightblue box_score_table"))
    else:
        return jsonify(boxscore1=table(df, "w3-striped lightblue box_score_table"))


@app.route('/test23/', methods=["GET", "POST"])
def test():

    return render_template('blog_load.html')


if __name__ == "__main__":
    app.run(debug=True, port="8070")
