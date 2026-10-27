import pickle
from collections import UserDict
from datetime import date, datetime, timedelta
from functools import wraps


class Field:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class Name(Field):
    def __init__(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Name cannot be empty.")
        super().__init__(value.strip())


class Phone(Field):
    def __init__(self, value):
        if not isinstance(value, str) or not value.isdigit() or len(value) != 10:
            raise ValueError("Phone number must contain exactly 10 digits.")
        super().__init__(value)


class Birthday(Field):
    def __init__(self, value):
        try:
            parsed_date = datetime.strptime(value, "%d.%m.%Y").date()
            if parsed_date.strftime("%d.%m.%Y") != value:
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError("Invalid date format. Use DD.MM.YYYY")

        super().__init__(value)

    @property
    def as_date(self):
        return datetime.strptime(self.value, "%d.%m.%Y").date()


class Record:
    def __init__(self, name):
        self.name = Name(name)
        self.phones = []
        self.birthday = None

    def add_phone(self, phone):
        self.phones.append(Phone(phone))

    def remove_phone(self, phone):
        phone_record = self.find_phone(phone)
        if phone_record is None:
            raise ValueError("Phone number not found.")
        self.phones.remove(phone_record)

    def edit_phone(self, old_phone, new_phone):
        phone_record = self.find_phone(old_phone)
        if phone_record is None:
            raise ValueError("Old phone number not found.")
        phone_record.value = Phone(new_phone).value

    def find_phone(self, phone):
        for phone_record in self.phones:
            if phone_record.value == phone:
                return phone_record
        return None

    def add_birthday(self, birthday):
        self.birthday = Birthday(birthday)

    def __str__(self):
        phones = ", ".join(phone.value for phone in self.phones) or "no phones"
        birthday = self.birthday.value if self.birthday else "not set"
        return (
            f"Contact name: {self.name.value}, "
            f"phones: {phones}, birthday: {birthday}"
        )


class AddressBook(UserDict):
    def add_record(self, record):
        self.data[record.name.value] = record

    def find(self, name):
        return self.data.get(name)

    def delete(self, name):
        if name not in self.data:
            raise KeyError(name)
        del self.data[name]

    @staticmethod
    def _birthday_in_year(birthday_date, year):
        try:
            return birthday_date.replace(year=year)
        except ValueError:
            return date(year, 3, 1)

    def get_upcoming_birthdays(self):
        today = date.today()
        upcoming_birthdays = []

        for record in self.data.values():
            if record.birthday is None:
                continue

            birthday_date = record.birthday.as_date
            next_birthday = self._birthday_in_year(
                birthday_date, today.year
            )

            if next_birthday < today:
                next_birthday = self._birthday_in_year(
                    birthday_date, today.year + 1
                )

            if 0 <= (next_birthday - today).days <= 7:
                if next_birthday.weekday() >= 5:
                    next_birthday += timedelta(
                        days=7 - next_birthday.weekday()
                    )

                upcoming_birthdays.append({
                    "name": record.name.value,
                    "birthday": next_birthday.strftime("%d.%m.%Y"),
                })

        return upcoming_birthdays

    def __str__(self):
        return "\n".join(
            str(record) for record in self.data.values()
        )


# Збереження адресної книги у файл
def save_data(book, filename="addressbook.pkl"):
    with open(filename, "wb") as file:
        pickle.dump(book, file)


# Завантаження адресної книги з файлу
def load_data(filename="addressbook.pkl"):
    try:
        with open(filename, "rb") as file:
            return pickle.load(file)
    except FileNotFoundError:
        return AddressBook()


def input_error(func):
    @wraps(func)
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            return str(e)
        except KeyError:
            return "Contact not found."
        except AttributeError:
            return "Contact not found."
        except IndexError:
            return "Not enough arguments."

    return inner


def require_args(args, count, usage):
    if len(args) < count:
        raise ValueError(
            f"Not enough arguments. Usage: {usage}"
        )


def parse_input(user_input):
    parts = user_input.strip().split()
    if not parts:
        return "", []
    return parts[0].lower(), parts[1:]


@input_error
def add_contact(args, book: AddressBook):
    require_args(args, 2, "add [name] [phone]")
    name, phone, *_ = args

    record = book.find(name)
    message = "Contact updated."

    if record is None:
        record = Record(name)
        book.add_record(record)
        message = "Contact added."

    try:
        record.add_phone(phone)
    except ValueError:
        if message == "Contact added.":
            book.delete(name)
        raise

    return message


@input_error
def change_contact(args, book: AddressBook):
    require_args(args, 3, "change [name] [old phone] [new phone]")
    name, old_phone, new_phone, *_ = args

    record = book.find(name)
    record.edit_phone(old_phone, new_phone)

    return "Phone number updated."


@input_error
def show_phone(args, book: AddressBook):
    require_args(args, 1, "phone [name]")
    name, *_ = args

    record = book.find(name)
    phones = ", ".join(phone.value for phone in record.phones)

    return phones if phones else "This contact has no phone numbers."


@input_error
def show_all(args, book: AddressBook):
    if not book:
        return "Address book is empty."
    return str(book)


@input_error
def add_birthday(args, book: AddressBook):
    require_args(args, 2, "add-birthday [name] [DD.MM.YYYY]")
    name, birthday, *_ = args

    record = book.find(name)
    record.add_birthday(birthday)

    return f"Birthday added for {name}."


@input_error
def show_birthday(args, book: AddressBook):
    require_args(args, 1, "show-birthday [name]")
    name, *_ = args

    record = book.find(name)

    if record.birthday is None:
        return f"Birthday is not set for {name}."

    return f"{name}'s birthday: {record.birthday.value}"


@input_error
def birthdays(args, book: AddressBook):
    upcoming = book.get_upcoming_birthdays()

    if not upcoming:
        return "No birthdays in the next 7 days."

    lines = ["Upcoming birthdays:"]

    for item in upcoming:
        lines.append(
            f"{item['name']}: congratulate on {item['birthday']}"
        )

    return "\n".join(lines)


def main():
    book = load_data()
    print("Welcome to the assistant bot!")

    try:
        while True:
            try:
                user_input = input("Enter a command: ")
            except (EOFError, KeyboardInterrupt):
                print("\nGood bye!")
                break

            command, args = parse_input(user_input)

            if not command:
                print("Please enter a command.")
            elif command in ("close", "exit"):
                print("Good bye!")
                break
            elif command == "hello":
                print("How can I help you?")
            elif command == "add":
                print(add_contact(args, book))
            elif command == "change":
                print(change_contact(args, book))
            elif command == "phone":
                print(show_phone(args, book))
            elif command == "all":
                print(show_all(args, book))
            elif command == "add-birthday":
                print(add_birthday(args, book))
            elif command == "show-birthday":
                print(show_birthday(args, book))
            elif command == "birthdays":
                print(birthdays(args, book))
            else:
                print("Invalid command.")
    finally:
        save_data(book)


if __name__ == "__main__":
    main()
