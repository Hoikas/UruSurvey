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

def _print_response(db, session, question):
    response = fetch_result(db, """SELECT flags,
                                          responses.value AS original,
                                          sanitize.value AS sanitized
                                   FROM responses
                                   LEFT JOIN sanitize ON sanitize.idx = responses.idx
                                   WHERE session = ? AND question = ?""",
                            (session, question))
    if response is None:
        raise RuntimeError(f"Could not get response from session {session}")
    if not (response["flags"] & ResponseFlags.sanitized) and not response["original"]:
        return
    question_result = fetch_result(db, "SELECT value FROM questions WHERE idx = ?", (question,))
    if question_result is None:
        raise RuntimeError(f"Could not get question {question}")

    print(f"QUESTION: {question_result[0]}")
    print(f"RESPONSE: {response['original']}")
    if response["flags"] & ResponseFlags.sanitized:
        print(f"SANITIZE: {response['sanitized']}")
    print()

def main(args):
    with open_database(args.db_path) as db:
        if args.question == -1:
            question_ids = tuple(iter_results(db, "SELECT idx FROM questions"))
            for i in question_ids:
                _print_response(db, args.session, i[0])
        else:
            _print_response(db, args.session, args.question)
    return True