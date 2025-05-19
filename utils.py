import re

# Email validation function
def validate_college_email(email):
    """
    Validates that the email follows the college email format:
    16042(X)7(XXXXX)@mjcollege.ac.in.
    Where X represents any digit.
    """
    pattern = r'^16042\d{1}7\d{5}@mjcollege\.ac\.in$'
    if not re.match(pattern, email):
        return False
    return True