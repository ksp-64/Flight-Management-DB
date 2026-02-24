from AllFilterSpecs import FilterSpec

# Create a filters dict with all spec keys set to None.

def init_filters(specs: list[FilterSpec]) -> dict:
    return {s.key: None for s in specs}

def format_filters(filters: dict, specs: list[FilterSpec]) -> str:
    parts: list[str] = []
    for s in specs:
        v = filters.get(s.key)
        if v not in (None, ""):
            parts.append(f"{s.label}={v}")
    return ", ".join(parts) if parts else "(none)"

# Ask user which filter to update, then prompt for a value.

def prompt_filter(
    filters: dict,
    specs: list[FilterSpec],
    choose_from_list,
    prompt_optional,
    valid_statuses: list[str],
) -> None:
    label = choose_from_list("Filter to Update:", [s.label for s in specs])
    spec = next(s for s in specs if s.label == label)

    if spec.ui_kind == "status":
        filters[spec.key] = choose_from_list(spec.prompt or "Status: ", valid_statuses)
        return

    while True:
        raw = prompt_optional(spec.prompt or f"{spec.label}: ")
        if not raw:
            print("Invalid value. A value is required. Use -q to cancel.")
            continue

        if spec.ui_kind == "int":
            try:
                filters[spec.key] = int(raw)
                return
            except ValueError:
                print("Invalid value. Enter a whole number. Use -q to cancel.")
                continue

        if spec.ui_kind == "yes_no":
            v = raw.strip().lower()
            if v in ("y", "yes"):
                filters[spec.key] = "yes"
                return
            if v in ("n", "no"):
                filters[spec.key] = "no"
                return
            print("Invalid value. Enter Yes or No. Use -q to cancel.")
            continue

        # default: treat anything else as text
        filters[spec.key] = raw
        return

# Append WHERE clause + params for a single spec/value.

def apply_sql_filter(sql: str, params: list, spec: FilterSpec, value) -> str:
    if value in (None, "") or not spec.col:
        return sql

    kind = spec.sql_kind
    col = spec.col

    if kind == "like":
        params.append(f"%{value}%")
        return sql + f" AND {col} LIKE ?"

    if kind == "equal":
        params.append(value)
        return sql + f" AND {col} = ?"

    if kind == "equal_ci":
        params.append(value)
        return sql + f" AND {col} = ? COLLATE NOCASE"

    if kind == "presence":
        if value == "yes":
            return sql + f" AND {col} IS NOT NULL AND trim({col}) <> ''"
        if value == "no":
            return sql + f" AND ({col} IS NULL OR trim({col}) = '')"
        return sql

    raise ValueError(f"Unknown sql_kind: {kind}")
