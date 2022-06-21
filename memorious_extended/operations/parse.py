import csv
from urllib.parse import urljoin

import jq
from banal import clean_dict, ensure_dict
from memorious.helpers.rule import Rule
from memorious.operations.parse import URL_TAGS
from memorious.operations.parse import parse_for_metadata as memorious_parse_meta
from memorious.operations.parse import parse_html as memorious_parse_html
from normality import collapse_spaces
from servicelayer.cache import make_key

from ..incremental import skip_incremental
from ..pagination import paginate


def parse_jq(context, data):
    """
    parse a json response and emit data dict based on config:
    uses `jq` python implementation
    will emit data for each row of the jq result
    """
    res = context.http.rehash(data)
    jsondata = clean_dict(res.json)

    pattern = context.params["pattern"]
    res = jq.compile(pattern).input(jsondata)
    for item in res.all():
        context.emit(data={**data, **item})


def parse_html(context, data):
    """
    an extended parse to handle incremental scraping and pagination

    params:
        <all from memorious parse>
        emit: whether to emit the parsed data at the end (default: false)
        parse_html: whether to parse the html for links (default: true)
        pagination: see `pagination.py`
    """
    should_emit = context.params.get("emit") is True
    should_parse_html = context.params.get("parse_html", True) is True

    if not skip_incremental(context, data):
        with context.http.rehash(data) as result:
            if result.html is not None:
                # Get extra metadata from the DOM
                memorious_parse_meta(context, data, result.html)
                # maybe data is updated with unique identifier for incremental skip
                if not skip_incremental(context, data) and should_parse_html:
                    # emit urls from include paths
                    memorious_parse_html(context, data, result)

            # emit next page data if any
            paginate(context, data, result.html)

            rules = context.params.get("store") or {"match_all": {}}
            if Rule.get_rule(rules).apply(result):
                context.emit(rule="store", data=data)
            if should_emit:
                context.emit(data=data)


def parse_html_listing(context, data):
    """
    an extended parse to handle incremental scraping, pagination
    and parse a list of items, emit for each item

    params:
        items: xpath to list of items nodes
        emit: whether to emit the parsed data at the end (default: false)
        parse_html: whether to parse the html for links (default: true)
        <all other params from `parse_html`> will be applied to every item,
        except pagination
    """
    should_emit = context.params.get("emit") is True
    should_parse_html = context.params.get("parse_html", True) is True

    if not skip_incremental(context, data):
        with context.http.rehash(data) as result:
            if result.html is not None:
                for item in result.html.xpath(context.params["items"]):
                    item_data = {k: v for k, v in data.items()}
                    # Get extra metadata from the DOM
                    memorious_parse_meta(context, item_data, item)
                    # maybe data is updated with unique identifier for incremental skip
                    if not skip_incremental(context, item_data):
                        if should_parse_html:
                            # emit urls from include paths
                            _parse_html_part(context, item_data, item)
                        if should_emit:
                            # emit item data
                            context.emit(rule="item", data=item_data)

            paginate(context, data, result.html)
            rules = context.params.get("store") or {"match_all": {}}
            if Rule.get_rule(rules).apply(result):
                context.emit(rule="store", data=data)


def _parse_html_part(context, data, html):
    """
    rewritten from memorious.operations.parse:parse_html
    to not depend on `result` but a html fragment
    """
    context.log.info("Parse html part.")

    include = context.params.get("include_paths")
    if include is None:
        roots = [html]
    else:
        roots = []
        for path in include:
            roots = roots + html.xpath(path)

    seen = set()
    for root in roots:
        for tag_query, attr_name in URL_TAGS:
            for element in root.xpath(tag_query):
                attr = element.get(attr_name)
                if attr is None:
                    continue

                try:
                    url = urljoin(data["url"], attr)
                    key = url
                except Exception:
                    context.log.warning("Invalid URL: %r", attr)
                    continue

                if url is None or key is None or key in seen:
                    continue
                seen.add(key)

                tag = make_key(context.run_id, key)
                if context.check_tag(tag):
                    continue
                context.set_tag(tag, None)
                data["url"] = url

                if data.get("title") is None:
                    # Option to set the document title from the link text.
                    if context.get("link_title", False):
                        data["title"] = collapse_spaces(element.text_content())
                    elif element.get("title"):
                        data["title"] = collapse_spaces(element.get("title"))

                context.http.session.headers["Referer"] = url
                context.emit(rule="fetch", data=data)


def parse_csv(context, data):
    res = context.http.rehash(data)
    parserkwargs = ensure_dict(context.params)
    skiprows = parserkwargs.pop("skiprows", 0)
    reader = csv.DictReader(open(res.file_path), **parserkwargs)
    rows = []
    for i in range(skiprows):
        next(reader)
    for row in reader:
        context.emit("row", data=row, optional=True)
        rows.append(row)
    context.emit("rows", data={**data, **{"rows": rows}})


def parse_xml(context, data):
    res = context.http.rehash(data)
    if res.xml is not None:
        memorious_parse_meta(context, data, res.xml)
    context.emit(data=data)
