#    This file is part of UruSurvey
#
#    UruSurvey is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    UruSurvey is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with UruSurvey.  If not, see <http://www.gnu.org/licenses/>.

import collections
import functools

from _constants import *
from _utils import *

# Signals to the main script to check the db for us.
requires_valid_db = True

def _count_responses(db, question):
    result = fetch_result(db, "SELECT COUNT(idx) FROM responses WHERE question = ?", (question,))
    if result is None:
        raise RuntimeError(f"Could not count responses to question {question}")
    return result[0]

def _iter_responses(db, question, split=None):
    q = """SELECT flags,
                  responses.value AS original,
                  sanitize.value AS sanitized
           FROM responses
           LEFT JOIN sanitize ON sanitize.idx = responses.idx
           WHERE question = ?;"""
    for response in iter_results(db, q, (question,)):
        if response["flags"] & ResponseFlags.sanitized:
            value = response["sanitized"]
        else:
            value = response["original"]
        if value:
            if split is not None:
                for i in value.split(split):
                    yield i
            else:
                yield value

def _bar_graph_responses(db, output, question=-1, key="unknown", title="unknown"):
    print("Collecting data...")
    counter = collections.Counter()
    counter.update(_iter_responses(db, question, split=';'))
    response_count = _count_responses(db, question)
    data = collections.OrderedDict()
    for data_key, data_value in sorted(counter.items()):
        data.setdefault(key, []).append(data_key)
        data.setdefault("Percent", []).append(int(data_value / response_count * 100))
        data.setdefault("Count", []).append(data_value)

    print("Generating graph...")
    import pandas
    import plotly, plotly.express

    df = pandas.DataFrame(data)
    fig = plotly.express.bar(df, x=key, y="Percent", color="Percent", title=title,
                             hover_name=key, hover_data=["Count"])
    if output:
        plotly.offline.plot(fig, filename=str(output))
    else:
        fig.show()

def _pie_chart_responses(db, output, question=-1, title="unknown"):
    print("Collecting data...")
    counter = collections.Counter()
    counter.update(_iter_responses(db, question))

    print("Generating graph...")
    import plotly
    import plotly.graph_objects as go

    fig = go.Figure(data=go.Pie(labels=list(counter.keys()),
                                values=list(counter.values()),
                                hole=0.3),
                    layout_title_text=title)
    if output:
        plotly.offline.plot(fig, filename=str(output))
    else:
        fig.show()

def _print_help(db=None, output=None):
    options = ",".join(subcommands.keys())
    print(f"Graph commands: {options}")

# Graphing subcommand handlers...
subcommands = {
    "help": _print_help,

    # Simple bar graphs
    "shards": functools.partial(_bar_graph_responses, question=8,
                                key="Shard", title="Shards Played On"),
    "bots": functools.partial(_bar_graph_responses, question=10,
                              key="Bot", title="Bots Used"),
    "online_games": functools.partial(_bar_graph_responses, question=13,
                                      key="Game", title="Online Games Played"),
    "tools_used": functools.partial(_bar_graph_responses, question=27,
                                    key="Tool", title="Tools Used in Age Creation"),
    "max_versions": functools.partial(_bar_graph_responses, question=35,
                                      key="Version", title="Max Users: 3ds Max Versions"),

    # Simple pie charts
    "language": functools.partial(_pie_chart_responses, question=0,
                                  title="Native Language"),
    "i10n_english": functools.partial(_pie_chart_responses, question=1,
                                      title="Comfort Playing in English"),
    "i10n_preference": functools.partial(_pie_chart_responses, question=2,
                                         title="Prefer to Play in Native Language"),
    "i10n_volunteer": functools.partial(_pie_chart_responses, question=3,
                                        title="Willingness to Help Translate"),
    "os": functools.partial(_pie_chart_responses, question=4, title="OS Preference"),
    "mac_difficulty": functools.partial(_pie_chart_responses, question=5,
                                        title="Mac Difficulty in Playing URU"),
    "mac_problems": functools.partial(_pie_chart_responses, question=6,
                                      title="Mac Problems When Playing URU"),
    "mac_method": functools.partial(_pie_chart_responses, question=7,
                                    title="Method Used to Play URU on Macs"),
    "uru_favorite": functools.partial(_pie_chart_responses, question=9,
                                      title="Favorite Aspect of Playing URU"),
    "clients": functools.partial(_pie_chart_responses, question=11,
                                 title="Nonstandard Client Usage"),
    "sl": functools.partial(_pie_chart_responses, question=12,
                            title="Second Life Players"),
    "sl_or_uru": functools.partial(_pie_chart_responses, question=14,
                                   title="Which Game is Played More Frequently"),
    "sl_content_creation": functools.partial(_pie_chart_responses, question=16,
                                             title="SL Content Creation"),
    "uru_fan_visits": functools.partial(_pie_chart_responses, question=18,
                                        title="URU Fan Content Usage"),
    "uru_fan_age": functools.partial(_pie_chart_responses, question=24,
                                     title="Favorite URU Fan Age"),
    "uru_age_creation": functools.partial(_pie_chart_responses, question=25,
                                          title="Fan Age Creation"),
    "uru_fan_age_publish": functools.partial(_pie_chart_responses, question=26,
                                             title="Interest in Seeing Their Content Online"),
    "uru_favorite_tool": functools.partial(_pie_chart_responses, question=28,
                                           title="Most Frequently Used Age Creation Tool"),
    "max_experienced": functools.partial(_pie_chart_responses, question=30,
                                         title="Used 3ds Max Before URU"),
    "max_upgrade": functools.partial(_pie_chart_responses, question=32,
                                     title="Wants an Update 3ds Max Plugin Binary"),
    "max_blender_used": functools.partial(_pie_chart_responses, question=33,
                                          title="3ds Max Users: Last Version of Blender Used"),
    "korman_priority": functools.partial(_pie_chart_responses, question=38,
                                         title="Korman Development Priority"),
    "pyprp_new_blender": functools.partial(_pie_chart_responses, question=41,
                                           title="PyPRP Users: Used a Newer Blender Version"),
}

def main(args):
    try:
        subcommand = subcommands.get(args.subcommand)
        if subcommand is None:
            _print_help()
            return
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            if args.output.is_file():
                args.output.unlink()
        with open_database(args.db_path) as db:
            subcommand(db, args.output)
    except ImportError as ex:
        raise RuntimeError(f"{ex} -- did you install it?")
