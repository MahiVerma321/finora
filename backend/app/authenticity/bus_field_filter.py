
def filter_bus_generic_fields(generic_fields, specific_fields):
    """
    Apply bus-specific corrections to generic extraction results.

    Does not modify the shared field merger or affect flight/train.
    """
    filtered = dict(generic_fields)

    specific_seat = specific_fields.get("seat")
    generic_seat = filtered.get("seat")

    if specific_seat is not None and generic_seat is not None:
        specific_value = (
            specific_seat.get("value")
            if isinstance(specific_seat, dict)
            else specific_seat
        )

        generic_value = (
            generic_seat.get("value")
            if isinstance(generic_seat, dict)
            else generic_seat
        )

        # Reject a numeric-only generic seat when the
        # bus-specific extractor found a different seat.
        if (
            str(specific_value).strip().upper()
            != str(generic_value).strip().upper()
            and str(generic_value).strip().isdigit()
        ):
            filtered.pop("seat", None)

    return filtered
