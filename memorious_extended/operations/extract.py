import re

from banal import ensure_dict, ensure_list, is_mapping, clean_dict


def _extract_regex_groups(key, value, patterns, log):
    patterns = ensure_list(patterns)
    if is_mapping(value):
        value = value.get(key)
    if value is None:
        log(f"No data found in `{key}`")
        return {}
    for pattern in patterns:
        pattern = re.compile(pattern)  # yaml escaping & stuff
        m = re.match(pattern, value)
        if m is not None:
            return {k: v.strip() for k, v in clean_dict(m.groupdict().items())}
        if m is None:
            log("Can't extract data for `%s`: [%s] %s" % (key, pattern.pattern, value))
    return {}


def _extract_deep(config, key, value, patterns, log):
    pass


def regex_groups(context, data, emit=True):
    """
    extract named regex groups via regex from source keys in data that become new keys
    in data, leaving the source existing

    params:
        <source_key>: <regex_pattern> (or list of patterns, takes first matche)

    example:

        stage:
            method: memorious.operations.extract.regex_groups
            params:
                full_name: (?P<first_name>\w+)\s(?P<last_name>\w+)              # noqa

        with {"full_name": "John Doe"} as data input, this emits:
        {
            "full_name": "John Doe",
            "first_name": "John",
            "last_name": "Doe"
        }


    more advanced example:

        stage:
            method: memorious.operations.extract.regex_groups
            params:
                names:
                    store_as: authors
                    split: ","
                    patterns:
                        - (?P<first_name>\w+)\s(?P<last_name>\w+)            # noqa
                        - (?P<name>\w+)                                      # noqa

        with {"names": "John Doe, Alice"} as data input, this emits:
        {
            "names": "John Doe, Alice",
            "authors": [{
                "first_name": "John",
                "last_name": "Doe"
            }, {
                "name": "Alice"
            }]
        }


    """
    for key, patterns in ensure_dict(context.params).items():
        logger = context.log.warning
        if is_mapping(patterns):
            # more advanced extraction
            config = {k: v for k, v in patterns.items()}

            if key in data:
                patterns = ensure_list(config.pop("pattern", config.pop("patterns")))
                store_key = config.pop("store_as")
                separator = config.pop("split", None)

                if separator is not None:
                    # result will be a list of dictionaries
                    values = data[key].split(separator)
                    res = [
                        _extract_regex_groups(key, value, patterns, logger)
                        for value in values
                    ]

                else:
                    # result will be 1 dictionary
                    res = _extract_regex_groups(key, data, patterns, logger)

                data[store_key] = res

        else:
            # simple extraction
            data.update(_extract_regex_groups(key, data, patterns, logger))

    if emit:
        context.emit(data=data)
    else:
        # for cli reparsing
        return data
