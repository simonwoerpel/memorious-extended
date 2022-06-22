from pprint import pformat

from banal import clean_dict, ensure_dict
from furl import furl
from memorious.operations.fetch import fetch as memorious_fetch

from ..forms import get_form
from ..incremental import skip_incremental
from ..pagination import get_paginated_url
from ..util import generate_url


def _get_url(context, data):
    """
    get url from context params or data dict,
    log warning for no url found
    """
    url = context.params.get("url")
    if url is not None:
        return url.format(**data)
    url = data.get("url")
    if url is None:
        context.log.warning("No url found.")
    return url


def _get_headers(context):
    """
    return extra headers from context params as dict
    """
    return ensure_dict(context.params.get("headers"))


def apply_headers(context, data=None, emit=True):
    """
    apply headers to session context

    params:
        headers:
            X-Custom-Header: foobar
    """
    for key, value in _get_headers(context).items():
        context.http.session.headers[key] = value
    context.log.debug(f"Headers: {pformat(context.http.session.headers)}")
    if emit and data is not None:
        context.emit(data=data)


def fetch(context, data):
    """
    an extended fetch to be able to skip_incremental based on passed data dict
    and reduce fetches while testing
    with extra logic for url rewrite

    params:  # (all optional)
        headers: # see above
        base_url: # if url is not absolute, prepend this via url join
        rewrite:
            # replace
            method: replace
            data: ["<search-string>", "<replace-string>"]
            # template, data used from data dict
            method: template
            data: http://example.com/{{ foo }}
        pagination:
            param: p # url param name for page number, if a value for "page" is
                     # in data dict, it will be applied (e.g. http://example.com/?p=1)

    """
    apply_headers(context, emit=False)

    url = _get_url(context, data)
    url = get_paginated_url(context, data, url)

    if "rewrite" in context.params:
        method = context.params["rewrite"]["method"]
        method_data = context.params["rewrite"]["data"]
        if method == "replace":
            url = url.replace(*method_data)
        if method == "template":
            url = generate_url(method_data, data)

    if url is None:
        context.log.error("No url specified.")
        return

    f = furl(url)
    if f.scheme is None:
        if "base_url" in context.params:
            base_url = context.params["base_url"]
            url = furl(base_url).join(f).url
        elif "url" in data:
            url = furl(data["url"]).join(f).url

    if not skip_incremental(
        context, data, current_stage_test_runs=context.params.get("test_runs", 1)
    ):
        # do the actual fetch operation
        data["url"] = url
        memorious_fetch(context, data)


def _get_post_data(context, data):
    post_data = ensure_dict(context.params.get("data"))
    for post_key, data_key in ensure_dict(context.params.get("use_data")).items():
        post_data[post_key] = data.get(data_key)
    post_data = clean_dict(post_data)
    if not post_data:
        context.log.warning("No POST data.")
    return post_data


def _send_post_data(context, _data, **kwargs):
    url = _get_url(context, _data)
    if url is not None:
        context.log.debug(f"Post data: {pformat(kwargs)}")
        context.log.debug(f"Post url: {url}")
        res = context.http.post(url, headers=_get_headers(context), **kwargs)
        context.emit(data={**_data, **res.serialize()})
    else:
        context.log.warning("No url to post to.")


def post(context, data):
    """
    do a post request with optional data

    params:
        data: <dict data>
        use_data: (optional) <use data from data dict>
            new_key: old_key
        headers: (optional, see above)
    """
    post_data = _get_post_data(context, data)
    _send_post_data(context, data, data=post_data)


def post_json(context, data):
    """
    do a post request with json data

    params:
        data: <dict data>
        use_data: (optional) <use data from data dict>
            new_key: old_key
        headers: (optional, see above)
    """

    json_data = _get_post_data(context, data)
    _send_post_data(context, data, json=json_data)


def post_form(context, data):
    """
    do a post request to a form with its current data and extra data from params,
    takes the action of the form as endpoint url

    params:
        form: <xpath to form>
        data: <post data dict>
        use_data: (optional) <use data from data dict>
            new_key: old_key
        headers: (optional, see above)
    """
    form = context.params.get("form")

    if form:
        res = context.http.rehash(data)
        action, formdata = get_form(context, res.html, form)
        url = _get_url(context, data)
        url = furl(url).join(action).url
        post_data = _get_post_data(context, data)
        post_data = {**formdata, **post_data}
        _send_post_data(context, data, data=post_data)
