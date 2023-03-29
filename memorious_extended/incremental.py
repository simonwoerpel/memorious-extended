import re

from banal import ensure_dict, ensure_list
from memorious import settings
from servicelayer import env
from servicelayer.cache import make_key

from .util import get_value_from_xp as x


SKIP_INCREMENTAL = env.to_bool("MEMORIOUS_SKIP_INCREMENTAL", True)


def should_skip_incremental(context, data, config=None):
    """
    a more advanced skip_incremental implementation

    based on a "target" that should be reached, like storing a pdf,
    the scraper should incrementally skip before if the target was
    already reached

    the data is passed along the pipeline and if the target stage
    was executed successfully, it will set the tag key

    params:
      skip_incremental:
        key:  # generate tag key based on xpath, data dict or urlpattern
            data: ... (default: url)
            xpath: ...
            urlpattern: ...
        target: # optional, see default:
            store (name of target stage, default "store")

    (can also be passed in as dict for config parameter)
    """
    if config is None and not context.params.get("skip_incremental"):
        return False

    config = ensure_dict(config or context.params.get("skip_incremental"))
    get_key = ensure_dict(config.get("key"))
    identifier = None

    for key in ensure_list(get_key.get("data")):
        if key in data:
            identifier = data[key]
            break

    if identifier is None:
        urlpattern = get_key.get("urlpattern")
        if urlpattern is not None:
            url = data.get("url", "")
            if re.match(urlpattern, url):
                identifier = url

    if identifier is None:
        xpath = get_key.get("xpath")
        if xpath is not None:
            res = context.http.rehash(data)
            if hasattr(res, "html"):
                identifier = x(xpath, res.html)

    if identifier is None:
        # default: url
        identifier = data.get("url")

    if identifier is not None:
        target = config.get("target", "store")
        target_key = make_key("skip_incremental", identifier, target)
        data["skip_incremental"] = {"target": target, "key": target_key}
        if not settings.INCREMENTAL or not SKIP_INCREMENTAL:
            return False
        if context.check_tag(target_key):
            # we reached the target
            if settings.INCREMENTAL and SKIP_INCREMENTAL:
                context.log.info("Skipping: %s" % target_key)
                return True


def skip_while_testing(context, stage=None, key=None, counter=-1):
    # try to speed up tests...
    if not env.to_bool("TESTING_MODE"):
        return False

    key = make_key(
        "skip_while_testing",
        context.crawler,
        stage or context.stage,
        context.run_id,
        key,
    )
    tag = context.get_tag(key)
    if tag is None:
        context.set_tag(key, 0)
        return False
    if tag >= counter:
        context.log.debug("Skipping: %s" % key)
        return True
    context.set_tag(key, tag + 1)


def skip_incremental(
    context,
    data,
    config=None,
    previous_stage_test_runs=1,
    current_stage_test_runs=1,
    test_loops=None,
):
    """
    set up some incremental logic and pass through skip_incremental

    testing logic:
    if the "current" stage is reached X times, the "previous" will be marked
    as to skip for all next executions to speed up test run
    """
    # production use of skip_incremental
    if should_skip_incremental(context, data, config):
        return True

    if env.to_bool("TESTING_MODE"):
        # we reached the last stage?
        if data.get("skip_incremental", {}).get("target") == context.stage.name:
            context.log.debug("Cancelling crawler run because of test mode.")
            context.crawler.cancel()
            return

        # track recursion
        recursion = data.get(f"{context.stage}_recursion", 0)
        test_loops = context.get("test_loops", test_loops)
        if (test_loops is not None and recursion < test_loops) or test_loops is None:
            recursion += 1
        data[f"{context.stage}_recursion"] = recursion
        context.log.debug(f"{context.stage} recursion: {recursion} (of {test_loops})")
        previous_stage = data["previous_stage"] = data.get("current_stage")
        current_stage = data["current_stage"] = context.stage.name

        previous_finished = False
        current_finished = False

        if previous_stage is not None:
            # update counting for previous stage
            previous_recursion = data.get(f"{previous_stage}_recursion", 0)
            previous_finished = skip_while_testing(
                context, previous_stage, previous_recursion, previous_stage_test_runs
            )
            if previous_finished:
                context.log.debug(
                    f"Testing: finished stage `{previous_stage}_{previous_recursion}`"
                )

        if previous_stage is None or previous_finished:
            # update counting for current stage
            current_finished = skip_while_testing(
                context, current_stage, recursion, current_stage_test_runs
            )
        return current_finished
