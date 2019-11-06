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
