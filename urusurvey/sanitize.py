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

from _constants import *
from _utils import *

# Signals to the main script to check the db for us.
requires_valid_db = True

def _sanitize_by_question(db, i, show_all=False):
    responses = fetch_result(db, "SELECT idx FROM responses WHERE question = ?", (i,))
    if responses is None:
        raise RuntimeError(f"Unable to find responses to question {i}")

    for j, response in enumerate(responses):
        _sanitize_response(db, response[0], print_question=(j==0), show_all=show_all)

def _sanitize_by_session(db, i, show_all=False):
    responses = fetch_result(db, "SELECT idx FROM responses WHERE session = ?", (i,))
    if responses is None:
        raise RuntimeError(f"Unable to find responses to session {i}")

    for response in responses:
        _sanitize_response(db, response[0], show_all=show_all)

def _sanitize_response(db, i, **kwargs):
    response = fetch_result(db, """SELECT responses.idx AS response_idx,
                                          responses.session AS session_idx,
                                          responses.question AS question_idx,
                                          flags,
                                          responses.value AS original,
                                          sanitize.value AS sanitized,
                                          questions.value AS question
                                   FROM responses
                                   LEFT JOIN sanitize ON sanitize.idx = responses.idx
                                   LEFT JOIN questions ON questions.idx = responses.question
                                   WHERE responses.idx = ?;""", (i,))
    if response is None:
        raise RuntimeError(f"Unable to find response id {i}")

    been_sanitized = response["flags"] & ResponseFlags.sanitized
    valid_response = response["flags"] & ResponseFlags.valid
    if not (kwargs.get("show_all", False) or kwargs.get("force", False)) and \
           (been_sanitized or not valid_response):
       return

    # Probably shouldn't obey show_all because these are dead answers?
    if not kwargs.get("force", False) and not response["original"]:
        return

    print_help = False
    while True:
        if print_help:
            print("s - manually enter a sanitized response")
            print("d - discard this response (shortcut for setting an empty sanitize)")
            print("v - verify this as a valid response and don't show it again")
            print("u - undo all sanitization actions")
            print("n - nothing, skip over this and wait until later...")
            print("? - shows this help")
            print("SIGINT - save and exit")
            print()
            print_help = False

        print(f"S:{response['session_idx']} Q:{response['question_idx']} R:{response['response_idx']}")
        if kwargs.get("print_question", True):
            print(f"QUESTION: {response['question']}")
        if kwargs.get("print_response", True):
            print(f"RESPONSE: {response['original']}")
        if kwargs.get("print_sanitized", True) and been_sanitized:
            print(f"SANITIZE: {response['sanitized']}")
        print()

        cmd = input("What should we do with this response? [s,d,v,u,n,?] ").lower().strip()
        if cmd == "s":
            print("Enter the new response value:")
            sanitized = input("> ").strip()
            if not sanitized:
                print("Error: no value entered, use 'd' to discard.")
                continue
            break
        elif cmd == "d":
            sanitized = ""
            break
        elif cmd == "v":
            sanitized = None
            break
        elif cmd == "u":
            sanitized = False
            break
        elif cmd == "n":
            return
        else:
            print_help = True
            continue

    with db:
        if sanitized is None:
            # This response is valid, mark that in the database.
            flags = response["flags"] | ResponseFlags.valid
        elif sanitized is False:
            flags = ResponseFlags.none
            db.execute("DELETE FROM sanitize WHERE idx = ?;", (response["response_idx"],))
        else:
            # We have a sanitized response to add...
            flags = response["flags"] | ResponseFlags.sanitized
            db.execute("INSERT INTO sanitize (idx, value) VALUES (?, ?);",
                       (response["response_idx"], sanitized))
        db.execute("UPDATE responses SET flags = ? WHERE idx = ?;", (flags, response["response_idx"]))

def main(args):
    try:
        with open_database(args.db_path) as db:
            if args.question:
                _sanitize_by_question(db, args.index, args.all)
            elif args.session:
                _sanitize_by_session(db, args.index, args.all)
            elif args.index >= 0:
                _sanitize_response(db, args.index, force=True)
            else:
                raise RuntimeError("No sanitize mode was set!")
    except KeyboardInterrupt:
        print()
