from rapidfuzz import fuzz

print(
    fuzz.partial_ratio(
        "pramav",
        "pranav"
    )
)