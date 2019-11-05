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

from contextlib import contextmanager
import sqlite3

def fetch_result(db, query, *args, **kwargs):
    cursor = db.cursor()
    try:
        cursor.execute(query, *args, **kwargs)
        return cursor.fetchone()
    finally:
        cursor.close()

def iter_results(db, query, *args, **kwargs):
    cursor = db.cursor()
    try:
        cursor.execute(query, *args, **kwargs)
        while True:
            result = cursor.fetchone()
            if result is None:
                break
            yield result
    finally:
        cursor.close()

@contextmanager
def open_database(*args, **kwargs):
    connection = sqlite3.connect(*args, **kwargs)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()
