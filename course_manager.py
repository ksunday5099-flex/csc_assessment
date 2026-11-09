"""Student Course Management System (COS 201 mid-semester lab project).

A console application for recording the courses a student is taking in a
semester. Run it with:

    python3 course_manager.py
"""

import csv
import os
import re

CODE_PATTERN = re.compile(r"^[A-Z]{2,4}\d{3}$")
MIN_UNITS = 1
MAX_UNITS = 6
MAX_COURSES = 100
DEFAULT_FILE = "courses.csv"
CSV_HEADER = ["code", "title", "units"]


class CourseError(Exception):
    """Base class for errors the user can understand and correct."""


class InvalidCourseError(CourseError):
    """A course field failed validation."""


class DuplicateCourseError(CourseError):
    """A course with the same code has already been added."""


class CourseLimitError(CourseError):
    """The course list is full."""


class CourseFileError(CourseError):
    """A course file could not be read or written."""


class Course:
    """A single course. Values are cleaned and validated on creation."""

    def __init__(self, code, title, units):
        self.code = Course.clean_code(code)
        self.title = Course.clean_title(title)
        self.units = Course.clean_units(units)

    @staticmethod
    def clean_code(raw):
        """Turn input such as ' cos 201 ' into 'COS201', or raise an error."""
        code = "".join(raw.split()).upper()
        if not code:
            raise InvalidCourseError("Course code cannot be empty.")
        if not CODE_PATTERN.match(code):
            raise InvalidCourseError(
                "Course code must be 2-4 letters followed by 3 digits, e.g. COS201."
            )
        return code

    @staticmethod
    def clean_title(raw):
        """Trim the title and collapse repeated spaces."""
        title = " ".join(raw.split())
        if not title:
            raise InvalidCourseError("Course title cannot be empty.")
        return title

    @staticmethod
    def clean_units(raw):
        """Convert units to a whole number within the allowed range."""
        try:
            units = int(str(raw).strip())
        except ValueError:
            raise InvalidCourseError("Units must be a whole number.") from None
        if not MIN_UNITS <= units <= MAX_UNITS:
            raise InvalidCourseError(
                f"Units must be between {MIN_UNITS} and {MAX_UNITS}."
            )
        return units


class CourseManager:
    """Stores the course list and performs operations on it."""

    def __init__(self):
        self.courses = []
        self.has_unsaved_changes = False

    def add_course(self, course):
        """Add a course, rejecting duplicates and enforcing the size limit."""
        if len(self.courses) >= MAX_COURSES:
            raise CourseLimitError(f"The list is full ({MAX_COURSES} courses).")
        if self.search_by_code(course.code) is not None:
            raise DuplicateCourseError(f"{course.code} has already been added.")
        self.courses.append(course)
        self.has_unsaved_changes = True

    def search_by_code(self, code, index=0):
        """Recursively look for a course by code; return it, or None.

        Base cases: the end of the list, or a matching course.
        Recursive case: search the rest of the list.
        """
        if index >= len(self.courses):
            return None
        if self.courses[index].code == code:
            return self.courses[index]
        return self.search_by_code(code, index + 1)

    def total_units(self, index=0):
        """Recursively add up the units from `index` to the end of the list."""
        if index >= len(self.courses):
            return 0
        return self.courses[index].units + self.total_units(index + 1)

    def save_to_file(self, path):
        """Write all courses to a CSV file.

        The data goes to a temporary file first, so a failed save cannot
        damage an existing file.
        """
        temp_path = f"{path}.tmp"
        try:
            with open(temp_path, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(CSV_HEADER)
                for course in self.courses:
                    writer.writerow([course.code, course.title, course.units])
            os.replace(temp_path, path)
        except OSError as error:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise CourseFileError(f"Could not save '{path}': {error}") from error
        self.has_unsaved_changes = False

    def load_from_file(self, path):
        """Replace the current list with the courses in a CSV file.

        Invalid rows are skipped and returned as messages. The current list
        is only replaced once the file has been read successfully.
        """
        loaded = CourseManager()
        problems = []
        try:
            with open(path, newline="", encoding="utf-8") as file:
                reader = csv.reader(file)
                header = next(reader, None)
                if header != CSV_HEADER:
                    raise CourseFileError(
                        f"'{path}' is not a course file (expected the header "
                        f"{','.join(CSV_HEADER)})."
                    )
                for row in reader:
                    if not row:
                        continue
                    line = reader.line_num
                    if len(row) != len(CSV_HEADER):
                        problems.append(f"Line {line}: expected 3 values.")
                        continue
                    try:
                        loaded.add_course(Course(*row))
                    except CourseError as error:
                        problems.append(f"Line {line}: {error}")
        except FileNotFoundError:
            raise CourseFileError(f"File '{path}' was not found.") from None
        except (OSError, UnicodeDecodeError, csv.Error) as error:
            raise CourseFileError(f"Could not read '{path}': {error}") from error

        if problems and not loaded.courses:
            raise CourseFileError(f"'{path}' has no valid courses: {problems[0]}")

        self.courses = loaded.courses
        self.has_unsaved_changes = False
        return problems


class ConsoleApp:
    """The text-based menu that connects the user to the CourseManager."""

    def __init__(self, manager=None):
        self.manager = manager if manager is not None else CourseManager()
        self.running = True
        self.menu = {
            "1": ("Add Course", self.add_course),
            "2": ("View All Courses", self.view_courses),
            "3": ("Search Course by Code", self.search_course),
            "4": ("Compute Total Units", self.show_total_units),
            "5": ("Save to File", self.save_courses),
            "6": ("Load from File", self.load_courses),
            "7": ("Exit Program", self.exit_program),
        }

    def run(self):
        """Show the menu repeatedly until the user chooses to exit."""
        print("=" * 44)
        print(" STUDENT COURSE MANAGEMENT SYSTEM")
        print("=" * 44)
        try:
            while self.running:
                self.show_menu()
                choice = input("Choose an option (1-7): ").strip()
                if choice in self.menu:
                    print()
                    self.menu[choice][1]()
                else:
                    print("Invalid option. Please enter a number from 1 to 7.")
        except (EOFError, KeyboardInterrupt):
            print("\nInput closed. Exiting without saving.")

    def show_menu(self):
        print()
        for key, (label, _) in self.menu.items():
            print(f"  {key}. {label}")

    def ask(self, prompt, clean):
        """Keep asking until `clean` accepts the input. Blank input cancels."""
        while True:
            raw = input(f"{prompt} (blank to cancel): ").strip()
            if not raw:
                print("Cancelled.")
                return None
            try:
                return clean(raw)
            except InvalidCourseError as error:
                print(f"  Error: {error}")

    def confirm(self, prompt):
        """Keep asking until the user answers yes or no."""
        while True:
            answer = input(f"{prompt} (y/n): ").strip().lower()
            if answer in ("y", "yes"):
                return True
            if answer in ("n", "no"):
                return False
            print("  Please answer y or n.")

    def add_course(self):
        code = self.ask("Course code", Course.clean_code)
        if code is None:
            return
        if self.manager.search_by_code(code) is not None:
            print(f"Error: {code} has already been added.")
            return
        title = self.ask("Course title", Course.clean_title)
        if title is None:
            return
        units = self.ask("Units", Course.clean_units)
        if units is None:
            return
        try:
            self.manager.add_course(Course(code, title, units))
            print(f"Added {code}.")
        except CourseError as error:
            print(f"Error: {error}")

    def view_courses(self):
        courses = self.manager.courses
        if not courses:
            print("No courses recorded yet.")
            return
        width = max(len("Title"), max(len(course.title) for course in courses))
        print(f"{'No.':<4} {'Code':<8} {'Title':<{width}} Units")
        print("-" * (4 + 1 + 8 + 1 + width + 1 + 5))
        for number, course in enumerate(courses, start=1):
            print(
                f"{number:<4} {course.code:<8} {course.title:<{width}} "
                f"{course.units:>5}"
            )

    def search_course(self):
        code = self.ask("Course code to search for", Course.clean_code)
        if code is None:
            return
        course = self.manager.search_by_code(code)
        if course is None:
            print(f"No course found with code {code}.")
        else:
            print(f"Found: {course.code} - {course.title} ({course.units} units)")

    def show_total_units(self):
        count = len(self.manager.courses)
        print(f"Total units: {self.manager.total_units()} across {count} course(s).")

    def save_courses(self):
        path = self.ask_file_name()
        try:
            self.manager.save_to_file(path)
            print(f"Saved {len(self.manager.courses)} course(s) to '{path}'.")
        except CourseFileError as error:
            print(f"Error: {error}")

    def load_courses(self):
        if self.manager.has_unsaved_changes and not self.confirm(
            "Loading replaces your unsaved changes. Continue?"
        ):
            print("Load cancelled.")
            return
        path = self.ask_file_name()
        try:
            problems = self.manager.load_from_file(path)
            print(f"Loaded {len(self.manager.courses)} course(s) from '{path}'.")
            for problem in problems:
                print(f"  Skipped - {problem}")
        except CourseFileError as error:
            print(f"Error: {error}")

    def ask_file_name(self):
        name = input(f"File name [{DEFAULT_FILE}]: ").strip()
        return name or DEFAULT_FILE

    def exit_program(self):
        if self.manager.has_unsaved_changes and self.confirm(
            "You have unsaved changes. Save before exiting?"
        ):
            self.save_courses()
            if self.manager.has_unsaved_changes:
                print("Save failed, so the program is still open.")
                return
        self.running = False
        print("Goodbye!")


if __name__ == "__main__":
    ConsoleApp().run()