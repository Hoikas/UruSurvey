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

import _arguments
import importlib
import sys

if __name__ == "__main__":
    args = _arguments.main_parser.parse_args()
    print(f"{_arguments.program_description} starting...")

    # Commands are just modules with a main() function
    module = importlib.import_module(args.command)
    if getattr(module, "requires_valid_db", False):
        if not args.db_path.is_file():
            print("Error: Survey database is not available.")
            sys.exit(1)

    try:
        module.main(args)
    except RuntimeError as ex:
        print(f"Error: {ex}")
    finally:
        print("Have a nice day.")
