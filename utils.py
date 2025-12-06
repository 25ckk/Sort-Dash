# utils.py

def parse_input_list(input_text):
    """
    Turns "5,3,8,1" into [5, 3, 8, 1].
    Returns (list, error_message)
    """
    try:
        if not input_text.strip():
            return None, "Input list is empty."

        arr = [int(x.strip()) for x in input_text.split(",")]
        return arr, None

    except ValueError:
        return None, "Invalid input. Make sure you enter integers separated by commas."
