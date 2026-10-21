"""Custom tools for the chat.

Each tool is a function that gets the user's message and returns a Markdown answer.
If a tool can't understand the message it returns None, and the AI answers instead.
The TOOLS list at the bottom says which words pick each tool.
"""

import ast
import calendar
import math
import operator
import random
import re
import secrets
import string
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from tool_manager import Tool


# ---------- Helpers ----------


def numbers(text):
    """All numbers in the text, in order: 'roll 2 dice, 6.5' -> [2.0, 6.5]. '1-100' gives 1 and 100."""
    return [float(n) for n in re.findall(r"(?<![\d.])-?\d+(?:\.\d+)?", text)]


def payload(text, words):
    """The text a tool should work on: what's in "quotes", after a colon, or the message minus the command words."""
    quoted = re.search(r"[\"“](.+?)[\"”]", text)
    if quoted:
        return quoted.group(1)
    if ":" in text:
        return text.split(":", 1)[1].strip()
    for word in sorted(words, key=len, reverse=True):
        text = re.sub(rf"(?<![a-z]){re.escape(word)}(?![a-z])", "", text, flags=re.IGNORECASE)
    return text.strip(" ?!.")


def find_date(text):
    """The first YYYY-MM-DD date in the text, or None."""
    match = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    return date(*map(int, match.groups())) if match else None


# ---------- Date and time ----------

CITY_ZONES = {
    "dubai": "Asia/Dubai",
    "abu dhabi": "Asia/Dubai",
    "riyadh": "Asia/Riyadh",
    "karachi": "Asia/Karachi",
    "india": "Asia/Kolkata",
    "mumbai": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "singapore": "Asia/Singapore",
    "tokyo": "Asia/Tokyo",
    "sydney": "Australia/Sydney",
    "london": "Europe/London",
    "paris": "Europe/Paris",
    "new york": "America/New_York",
    "los angeles": "America/Los_Angeles",
}


def get_time(text):
    lower = text.lower()
    for city, zone in CITY_ZONES.items():
        if re.search(rf"\b{city}\b", lower):
            now = datetime.now(ZoneInfo(zone))
            return f"The time in {city.title()} is **{now:%I:%M %p}**."
    return f"The time is **{datetime.now():%I:%M %p}**."


def get_date(text):
    return f"Today is **{date.today():%A, %d %B %Y}**."


HOLIDAYS = {"christmas": (12, 25), "new year": (1, 1), "valentine": (2, 14), "halloween": (10, 31)}


def days_until(text):
    today = date.today()
    target = find_date(text)
    if target is None:
        for name, (month, day) in HOLIDAYS.items():
            if name in text.lower():
                target = date(today.year, month, day)
                if target < today:
                    target = target.replace(year=today.year + 1)
                break
    if target is None:
        return None
    days = (target - today).days
    if days < 0:
        return f"{target:%d %B %Y} was **{-days} days ago**."
    return f"**{days} days** until {target:%d %B %Y}."


def calculate_age(text):
    today = date.today()
    born = find_date(text)
    if born:
        if born > today:
            return "That date is in the future!"
        years = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        return f"Born on {born:%d %B %Y}, you are **{years} years old**."
    year = re.search(r"\b(?:19|20)\d{2}\b", text)
    if year:
        age = today.year - int(year.group())
        return f"Born in {year.group()}, you are **{age - 1} or {age} years old** (depends on your birthday)."
    return None


def check_leap_year(text):
    found = numbers(text)
    year = int(found[0]) if found else date.today().year
    if calendar.isleap(year):
        return f"**{year} is a leap year** (February has 29 days)."
    return f"**{year} is not a leap year.**"


# ---------- Random fun ----------


def generate_password(text):
    found = numbers(text)
    length = max(6, min(int(found[0]) if found else 12, 64))
    symbols = "!@#$%^&*-_?"
    # One of each kind of character, then fill the rest and shuffle
    chars = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice(symbols),
    ]
    chars += [secrets.choice(string.ascii_letters + string.digits + symbols) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(chars)
    return f"Here is a {length}-character password:\n\n```\n{''.join(chars)}\n```"


def roll_dice(text):
    lower = text.lower()
    sides = re.search(r"(?<![a-z])d(\d+)", lower)  # "d20" means a 20-sided die
    count = re.search(r"(\d+)\s*(?:dice|die|d\d)", lower)
    sides = max(2, min(int(sides.group(1)) if sides else 6, 1000))
    count = max(1, min(int(count.group(1)) if count else 1, 20))
    rolls = [random.randint(1, sides) for _ in range(count)]
    if count == 1:
        return f"You rolled a **{rolls[0]}** (d{sides})."
    return f"You rolled {', '.join(map(str, rolls))}, total **{sum(rolls)}** ({count}d{sides})."


def flip_coin(text):
    return f"It's **{random.choice(['Heads', 'Tails'])}**!"


def random_number(text):
    found = [int(n) for n in numbers(text)][:2]
    if len(found) == 2:
        low, high = sorted(found)
    elif found:
        low, high = sorted((1, found[0]))
    else:
        low, high = 1, 100
    return f"Your random number between {low} and {high} is **{random.randint(low, high)}**."


def generate_uuid(text):
    return f"Here is a new UUID:\n\n```\n{uuid.uuid4()}\n```"


def random_color(text):
    red, green, blue = (random.randint(0, 255) for _ in range(3))
    return f"Your random color is **#{red:02X}{green:02X}{blue:02X}** (RGB {red}, {green}, {blue})."


JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "I told my computer I needed a break, and it said: 'No problem, I'll go to sleep.'",
    "Why did the developer go broke? Because he used up all his cache.",
    "There are 10 kinds of people: those who understand binary and those who don't.",
    "Why was the math book sad? It had too many problems.",
    "What do you call a fake noodle? An impasta.",
    "Why don't skeletons fight each other? They don't have the guts.",
]


def tell_joke(text):
    return random.choice(JOKES)


QUOTES = [
    "“The secret of getting ahead is getting started.” — Mark Twain",
    "“It always seems impossible until it's done.” — Nelson Mandela",
    "“Don't watch the clock; do what it does. Keep going.” — Sam Levenson",
    "“Simplicity is the soul of efficiency.” — Austin Freeman",
    "“First, solve the problem. Then, write the code.” — John Johnson",
    "“Whether you think you can or you think you can't, you're right.” — Henry Ford",
]


def get_quote(text):
    return random.choice(QUOTES)


FACTS = [
    "Honey never spoils. Archaeologists have found 3,000-year-old honey that is still edible.",
    "Octopuses have three hearts and blue blood.",
    "A day on Venus is longer than a year on Venus.",
    "Bananas are berries, but strawberries are not.",
    "The first computer bug was a real moth, found in a Harvard computer in 1947.",
    "Sharks existed before trees.",
]


def fun_fact(text):
    return random.choice(FACTS)


EIGHT_BALL = [
    "It is certain.",
    "Without a doubt.",
    "Yes, definitely.",
    "Most likely.",
    "Ask again later.",
    "Cannot predict now.",
    "Don't count on it.",
    "My sources say no.",
    "Very doubtful.",
]


def magic_8_ball(text):
    return f"🎱 {random.choice(EIGHT_BALL)}"


def choose_one(text):
    # "choose between pizza, burger or pasta" -> ["pizza", "burger", "pasta"]
    body = re.split(r"\b(?:between|from|choose|pick one|decide)\b|:", text, flags=re.IGNORECASE)[-1]
    options = [o.strip(" ?!.") for o in re.split(r",|\bor\b", body, flags=re.IGNORECASE)]
    options = [o for o in options if o]
    if len(options) < 2:
        return None
    return f"I choose: **{random.choice(options)}**"


# ---------- Math ----------

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def evaluate(node):
    """Work out a parsed math expression. Safer than eval(): only numbers and math operators are allowed."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
        left, right = evaluate(node.left), evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("that power is too big")
        return OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPERATORS:
        return OPERATORS[type(node.op)](evaluate(node.operand))
    raise ValueError("only numbers and + - * / % ^ ( ) are allowed")


def calculate(text):
    text = re.sub(r"(?<=\d)\s*[x×]\s*(?=\d)", "*", text).replace("÷", "/")
    expression = "".join(re.findall(r"[\d.+\-*/%^()\s]", text)).strip()
    if not re.search(r"\d", expression):
        return None
    try:
        result = evaluate(ast.parse(expression.replace("^", "**"), mode="eval").body)
    except ZeroDivisionError:
        return "You can't divide by zero."
    except (SyntaxError, ValueError) as error:
        return f"I couldn't work out `{expression}`: {error}"
    if isinstance(result, float):
        result = int(result) if result.is_integer() else round(result, 6)
    return f"`{expression}` = **{result}**"


def check_prime(text):
    found = numbers(text)
    if not found:
        return None
    n = int(found[0])
    if n > 10**12:
        return "That number is too big for me to check quickly."
    if n < 2:
        return f"**{n} is not prime.** Primes start at 2."
    for divisor in range(2, math.isqrt(n) + 1):
        if n % divisor == 0:
            return f"**{n} is not prime.** It divides by {divisor} ({divisor} × {n // divisor})."
    return f"**{n} is prime!**"


def calculate_bmi(text):
    found = numbers(text)
    if len(found) < 2:
        return None
    weight, height = found[0], found[1]
    if height > 3:
        height /= 100  # height was given in cm
    bmi = weight / height**2
    if bmi < 18.5:
        category = "underweight"
    elif bmi < 25:
        category = "normal weight"
    elif bmi < 30:
        category = "overweight"
    else:
        category = "obese"
    return f"Your BMI is **{bmi:.1f}** ({category})."


def calculate_tip(text):
    percent = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    rest = text.replace(percent.group(), "") if percent else text
    percent = float(percent.group(1)) if percent else 15
    found = numbers(rest)
    if not found:
        return None
    bill = found[0]
    tip = bill * percent / 100
    return f"A {percent:g}% tip on {bill:.2f} is **{tip:.2f}**, so the total is **{bill + tip:.2f}**."


# ---------- Converters ----------


def convert_temperature(text):
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*°?\s*(celsius|fahrenheit|c|f)\b", text.lower())
    if not match:
        return None
    value, unit = float(match.group(1)), match.group(2)[0]
    if unit == "c":
        return f"{value:g}°C = **{value * 9 / 5 + 32:.1f}°F**"
    return f"{value:g}°F = **{(value - 32) * 5 / 9:.1f}°C**"


def convert_length(text):
    match = re.search(r"(\d+(?:\.\d+)?)\s*(km|kilomet(?:er|re)s?|mi|miles?)\b", text.lower())
    if not match:
        return None
    value, unit = float(match.group(1)), match.group(2)
    if unit.startswith("k"):
        return f"{value:g} km = **{value * 0.621371:.2f} miles**"
    return f"{value:g} miles = **{value * 1.609344:.2f} km**"


# ---------- Text ----------


def count_words(text):
    body = payload(text, ["count the words in", "count words in", "count words", "word count", "how many words in"])
    if not body:
        return None
    words = re.findall(r"[\w']+", body)
    return f"That text has **{len(words)} words** and **{len(body)} characters**."


def reverse_text(text):
    body = payload(text, ["reverse"])
    return f"`{body[::-1]}`" if body else None


def change_case(text):
    lower = text.lower()
    body = payload(text, ["uppercase", "upper case", "lowercase", "lower case", "title case"])
    if not body:
        return None
    if "upper" in lower:
        return body.upper()
    if "lower" in lower:
        return body.lower()
    return body.title()


def check_palindrome(text):
    body = payload(text, ["palindrome"])
    # "is racecar a palindrome" -> "racecar"
    body = re.sub(r"^(?:check\s+)?(?:if\s+|whether\s+)?(?:is\s+)?", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\s+(?:is\s+)?(?:a|an)?\s*$", "", body, flags=re.IGNORECASE)
    letters = re.sub(r"[^a-z0-9]", "", body.lower())
    if not letters:
        return None
    if letters == letters[::-1]:
        return f"Yes! **{body}** is a palindrome."
    return f"No, **{body}** is not a palindrome."


# ---------- Tool list ----------

TOOLS = [
    Tool("Time", "Current time, or the time in a city", ["what time", "current time", "time now", "time in", "clock"], "What time is it in Tokyo?", get_time),
    Tool("Date", "Today's date", ["date", "what day"], "What's the date today?", get_date),
    Tool("Days until", "Days until a date or holiday", ["days until", "days till", "days left", "how many days", "countdown"], "How many days until Christmas?", days_until),
    Tool("Age calculator", "Your age from a birth date or year", ["how old", "my age", "age", "born"], "How old am I if I was born on 1995-06-15?", calculate_age),
    Tool("Leap year", "Check if a year is a leap year", ["leap year", "leap"], "Is 2028 a leap year?", check_leap_year),
    Tool("Password generator", "Strong random password", ["password", "passcode", "passphrase"], "Generate a 16 character password", generate_password),
    Tool("Dice roller", "Roll dice, e.g. 2 dice or a d20", ["dice", "die", "roll", "d20", "d6"], "Roll 2 dice", roll_dice),
    Tool("Coin flip", "Heads or tails", ["coin", "flip", "toss", "heads or tails"], "Flip a coin", flip_coin),
    Tool("Random number", "Random number in a range", ["random number", "pick a number", "number between"], "Random number between 1 and 50", random_number),
    Tool("UUID generator", "New unique ID", ["uuid", "guid", "unique id"], "Generate a UUID", generate_uuid),
    Tool("Random color", "Random hex color", ["random color", "random colour", "hex color", "color", "colour"], "Give me a random color", random_color),
    Tool("Joke", "A random joke", ["joke", "make me laugh", "funny"], "Tell me a joke", tell_joke),
    Tool("Quote", "Motivational quote", ["quote", "motivate", "motivation", "inspire"], "Give me a quote", get_quote),
    Tool("Fun fact", "A random fun fact", ["fun fact", "fact", "did you know"], "Tell me a fun fact", fun_fact),
    Tool("Magic 8-ball", "Answers yes/no questions", ["8 ball", "8-ball", "magic 8", "fortune"], "Magic 8 ball: will I pass the exam?", magic_8_ball),
    Tool("Decision maker", "Picks one option for you", ["choose", "pick one", "decide"], "Choose between pizza, burger or pasta", choose_one),
    Tool(
        "Calculator", "Math: + - * / % ^ ( )", ["calculate", "calc", "compute", "math"], "Calculate (12 + 8) * 3", calculate,
        pattern=r"^\s*(?:what is|what's|whats)?[\d.(\s]+(?:[-+*/%^x×÷]\s*[\d.()\s]+)+\??$",  # a sum like "12 + 7" or "what is 5 x 3"
    ),
    Tool("Prime checker", "Is a number prime?", ["prime"], "Is 97 prime?", check_prime),
    Tool("BMI calculator", "BMI from weight (kg) and height (cm)", ["bmi", "body mass"], "BMI 70 kg 175 cm", calculate_bmi),
    Tool("Tip calculator", "Tip and total for a bill", ["tip", "tips", "bill"], "Tip 15% on 80", calculate_tip),
    Tool(
        "Temperature converter", "Celsius ↔ Fahrenheit", ["celsius", "fahrenheit", "temperature"], "Convert 30 C to F", convert_temperature,
        pattern=r"\d\s*°?\s*[cf]\b",  # "30c" or "86 °F"
    ),
    Tool("Length converter", "Kilometres ↔ miles", ["km", "kilometer", "kilometers", "kilometre", "kilometres", "mile", "miles"], "Convert 10 km to miles", convert_length),
    Tool("Word counter", "Count words and characters", ["word count", "count words", "count the words", "how many words"], "Word count: the quick brown fox", count_words),
    Tool("Reverse text", "Write text backwards", ["reverse"], "Reverse: hello world", reverse_text),
    Tool("Text case", "UPPER, lower or Title case", ["uppercase", "upper case", "lowercase", "lower case", "title case"], "Uppercase: hello world", change_case),
    Tool("Palindrome checker", "Same forwards and backwards?", ["palindrome"], "Is racecar a palindrome?", check_palindrome),
]
