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

import argparse
from pathlib import Path

program_description = "Uru Survey"
main_parser = argparse.ArgumentParser(description=program_description)
main_parser.add_argument("--db-path", type=Path, help="survey database file", default="uru_survey.db")

sub_parsers = main_parser.add_subparsers(title="command", dest="command", required=True)

# Question command
question_parser = sub_parsers.add_parser("questions")

# Response command
response_parser = sub_parsers.add_parser("response")
response_parser.add_argument("-q", "--question", type=int, default=-1)
response_parser.add_argument("session", type=int, help="session index to view responses for")

# Sanitize command
sanitize_parser = sub_parsers.add_parser("sanitize")
sanitize_parser.add_argument("--all", action="store_true", help="displays responses that were previously sanitized")
sanitize_method = sanitize_parser.add_mutually_exclusive_group()
sanitize_method.add_argument("-q", "--question", action="store_true", help="sanitize responses by question index")
sanitize_method.add_argument("-s", "--session", action="store_true", help="sanitize responses by session index")
sanitize_parser.add_argument("-i", "--index", type=int, default=-1)

# Update command
update_parser = sub_parsers.add_parser("update")
update_parser.add_argument("csv_path", type=Path, help="survey csv file from google sheets")
