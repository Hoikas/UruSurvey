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
    return sum((1 if i else 0 for i in _iter_responses(db, question)))

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

def _output_fig(fig, output):
    import plotly.io

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.is_file():
            output.unlink()
        plotly.io.write_html(fig, file=str(output), auto_open=False)
    else:
        plotly.io.show(fig)

def _bar_graph_responses(db, output, question=-1, key="unknown", title="unknown"):
    print("Collecting data...")
    counter = collections.Counter()
    counter.update(_iter_responses(db, question, split=';'))
    response_count = _count_responses(db, question)
    data = collections.OrderedDict()
    for data_key, data_value in sorted(counter.items()):
        data.setdefault(key, []).append(data_key)
        data.setdefault("Percent", []).append(round((data_value / response_count) * 100, 2))
        data.setdefault("Count", []).append(data_value)

    print("Generating graph...")
    import pandas
    import plotly.express

    df = pandas.DataFrame(data)
    fig = plotly.express.bar(df, x=key, y="Percent", color="Percent", title=title,
                             hover_name=key, hover_data=["Count"])
    _output_fig(fig, output)

def _pie_chart_responses(db, output, question=-1, title="unknown"):
    print("Collecting data...")
    counter = collections.Counter()
    counter.update(_iter_responses(db, question))

    print("Generating graph...")
    import plotly.graph_objects as go

    fig = go.Figure(data=go.Pie(labels=list(counter.keys()),
                                values=list(counter.values()),
                                hole=0.3),
                    layout_title_text=title)
    _output_fig(fig, output)

def _sunburst_i10n(db, output):
    print("Collecting data...")

    keys = ["language", "comfort", "prefer", "volunteer"]
    def generate_data():
        user = collections.namedtuple("user", keys)
        q  = """SELECT language_response.flags AS language_flags,
                       language_response.value AS language_original,
                       language_sanitize.value AS language_sanitized,
                       comfort_response.value AS comfort_value,
                       prefer_response.value AS prefer_value,
                       volunteer_response.value AS volunteer_value
                FROM responses language_response
                LEFT JOIN sanitize language_sanitize ON language_sanitize.idx = language_response.idx
                LEFT JOIN responses comfort_response ON comfort_response.question = 1 AND
                                                        comfort_response.session = language_response.session
                LEFT JOIN responses prefer_response ON prefer_response.question = 2 AND
                                                       prefer_response.session = language_response.session
                LEFT JOIN responses volunteer_response ON volunteer_response.question = 3 AND
                                                          volunteer_response.session = language_response.session
                WHERE language_response.question = 0;"""
        for result in iter_results(db, q):
            if result["language_flags"] & ResponseFlags.sanitized:
                language = result["language_sanitized"]
            else:
                language = result["language_original"]
            if not language:
                continue
            yield user(language, result["comfort_value"], result["prefer_value"], result["volunteer_value"])

    # Probably not the best idea to have all this in memory. Luckily the dataset is not that large.
    # Ugh. What a mess.
    data_src = list(generate_data())
    counters = { key: collections.Counter(((i.language, getattr(i, key)) for i in data_src if getattr(i, key))) for key in keys }
    languages = counters.pop("language")

    data = collections.defaultdict(list)
    for key, counter in counters.items():
        for (language, _), count in languages.items():
            data[f"{key}_ids"].append(language)
            data[f"{key}_labels"].append(language)
            data[f"{key}_values"].append(count)
            data[f"{key}_parents"].append("Native Language")
        for (native_language, value), count in counter.items():
            data[f"{key}_ids"].append(f"{native_language} - {value}")
            data[f"{key}_labels"].append(value)
            data[f"{key}_values"].append(count)
            data[f"{key}_parents"].append(native_language)

    print("Generating graph...")
    import plotly.graph_objects as go

    buttons = []
    titles = {
        "comfort": "Comfortable Playing URU in English",
        "prefer": "Prefer to Play in Native Language",
        "volunteer": "Willingness to Volunteer for ULP",
    }
    fig = go.Figure()
    for i, key in enumerate(keys[1:]):
        fig.add_trace(go.Sunburst(labels=data[f"{key}_labels"], values=data[f"{key}_values"],
                                  parents=data[f"{key}_parents"], ids=data[f"{key}_ids"],
                                  branchvalues="total", visible=(i==0), name=key,
                                  hoverinfo="label+text+value+name+percent parent"))
        buttons.append({ "label": titles[key],
                         "method": "update",
                         "args": [{ "visible": [bool(j==i) for j in range(len(keys[1:]))] },
                                  { "title": titles[key] }],
                        })
        if i == 0:
            fig.update_layout(title_text=titles[key])
    fig.update_layout(updatemenus=[go.layout.Updatemenu(type="buttons", direction="up",
                                                        active=0, buttons=buttons)])
    _output_fig(fig, output)

def _sunburst_os(db, output):
    print("Collecting data...")

    def generate_os_wrappers():
        q = """SELECT os_response.value AS os,
                      wrapper_response.flags AS wrapper_flags,
                      wrapper_response.value AS wrapper_original,
                      wrapper_sanitize.value AS wrapper_sanitized
               FROM responses os_response
               LEFT JOIN responses wrapper_response ON wrapper_response.question = 7 AND
                                                       wrapper_response.session = os_response.session
               LEFT JOIN sanitize wrapper_sanitize ON wrapper_sanitize.idx = wrapper_response.idx
               WHERE os_response.question = 4;"""
        for result in iter_results(db, q):
            if result["wrapper_flags"] & ResponseFlags.sanitized:
                wrapper = result["wrapper_sanitized"]
            else:
                wrapper = result["wrapper_original"]
            yield result["os"], wrapper
            # ensure we count this for the case of the OS in general as well.
            if wrapper:
                yield result["os"], ""

    counter = collections.Counter()
    counter.update(generate_os_wrappers())
    ids, labels, parents, values = [], [], [], []
    for (os, wrapper), count in counter.items():
        if wrapper:
            ids.append(f"{os} - {wrapper}")
            labels.append(wrapper)
            parents.append(os)
            values.append(count)
        else:
            ids.append(os)
            labels.append(os)
            parents.append("Preferred OS")
            values.append(count)

    print("Generating graph...")
    import plotly.graph_objects as go

    fig = go.Figure(data=go.Sunburst(ids=ids, labels=labels, parents=parents, values=values,
                                     branchvalues="total", hoverinfo="label+text+value+name+percent parent"),
                    layout_title_text="OS and Wrapper Usage")
    _output_fig(fig, output)

def _print_help(db=None, output=None):
    options = ",".join(subcommands.keys())
    print(f"Graph commands: {options}")

def _draw_all_graphs(db, output):
    if not output:
        raise RuntimeError("Output path must be specified!")

    for name, func in subcommands.items():
        if name in {"help", "all"}:
            continue

        path = output.joinpath(name).with_suffix(".html")
        print()
        print(f"Outputing '{name}' @ {path}")
        func(db, path)

# Graphing subcommand handlers...
subcommands = {
    "help": _print_help,
    "all": _draw_all_graphs,

    # Sunbursts
    "i10n": _sunburst_i10n,
    "os_detail": _sunburst_os,

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
        with open_database(args.db_path) as db:
            subcommand(db, args.output)
    except ImportError as ex:
        raise RuntimeError(f"{ex} -- did you install it?")
