import re


def normalize_ugandan_phone(value):
    digits = re.sub(r"\D", "", str(value or ""))

    if digits.startswith("256"):
        national_number = digits[3:]
    elif digits.startswith("0"):
        national_number = digits[1:]
    else:
        national_number = digits

    if not re.fullmatch(r"7\d{8}", national_number):
        raise ValueError(
            "Enter a valid Ugandan mobile number, such as +256700000001."
        )

    return f"+256{national_number}"
