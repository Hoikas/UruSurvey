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

import csv
from _utils import open_database

db_schema = """
CREATE TABLE IF NOT EXISTS responses
    (idx INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE ON CONFLICT IGNORE NOT NULL,
     session INTEGER REFERENCES sessions (idx) NOT NULL,
     question INTEGER REFERENCES questions (idx) NOT NULL,
     flags INTEGER NOT NULL DEFAULT (0),
     value TEXT NOT NULL,
     CONSTRAINT user_response_constraint UNIQUE (session, question) ON CONFLICT IGNORE);

CREATE TABLE IF NOT EXISTS questions
     (idx INTEGER PRIMARY KEY ON CONFLICT IGNORE AUTOINCREMENT NOT NULL,
      value TEXT);

CREATE TABLE IF NOT EXISTS sanitize
    (idx INTEGER PRIMARY KEY ON CONFLICT REPLACE AUTOINCREMENT REFERENCES responses (idx) NOT NULL, 
     value TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS sessions
    (idx INTEGER PRIMARY KEY ON CONFLICT IGNORE AUTOINCREMENT NOT NULL,
     timestamp DATETIME NOT NULL);
"""

def _import_questions(db, questions):
    # First column is timestamp
    questions_iter = iter(questions)
    next(questions_iter)

    for i, question in enumerate(questions_iter):
        with db:
            db.execute("INSERT INTO questions (idx) VALUES (:idx);", { "idx": i })
            db.execute("UPDATE questions SET value = :question WHERE idx = :idx;",
                       { "idx": i, "question": question })

def _import_response(db, i, response):
    # First column is timestamp
    response_iter = iter(response)
    timestamp = next(response_iter)

    with db:
        db.execute("INSERT INTO sessions (idx, timestamp) VALUES (:idx, :timestamp);",
                   { "idx": i, "timestamp": timestamp })
        results = ((i, q, v.strip()) for q, v in enumerate(response_iter))
        db.executemany("INSERT INTO responses (session, question, value) VALUES (?, ?, ?)", results)

def main(args):
    if not args.csv_path.is_file():
        print("Error: CSV file does not exist")
        return False

    with open_database(args.db_path) as db:
        with db:
            db.executescript(db_schema)

        with args.csv_path.open(encoding="utf-8") as csv_file:
            csv_reader = csv.reader(csv_file)

            # First line contains the questions, so we'll handle it first.
            _import_questions(db, next(csv_reader))
            for i, response in enumerate(csv_reader):
                _import_response(db, i, response)

    print("Successfully updated survey database!")
    return True
