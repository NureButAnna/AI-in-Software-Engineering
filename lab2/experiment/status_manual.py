def matches_status(case, value):
    if value is None:
        return True
    return case.status == value