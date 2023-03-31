from setuptools import find_packages, setup

setup(
    name="memorious-extended",
    version="0.0.1",
    description="Extensions to memorious",
    long_description="",
    classifiers=[
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
    ],
    keywords="",
    author="Simon Wörpel",
    author_email="simon.woerpel@medienrevolte.de",
    url="http://github.com/simonwoerpel/memorious-extended",
    license="MIT",
    packages=find_packages(exclude=["ez_setup", "tests"]),
    namespace_packages=[],
    zip_safe=False,
    install_requires=["memorious", "furl", "jq", "ipdb", "jinja2", "zavod"],
    entry_points={
        # "console_scripts": ["memorious = memorious.cli:main"],
        # "memorious_extended.operations": [
        #     "headers = memorious_extended.operations.http:apply_headers",
        #     "fetch = memorious_extended.operations.http:fetch",
        #     "post_form = memorious_extended.operations.http:post_form",
        #     "post_json = memorious_extended.operations.http:post_json",
        #     "parse_jq = memorious_extended.operations.parse:parse_jq",
        #     "parse = memorious_extended.operations.parse:parse_html",
        #     "parse_listing = memorious_extended.operations.parse:parse_html_listing",
        #     "regex = memorious_extended.operations.extract:regex_groups",
        #     "store = memorious_extended.operations.store:store",
        #     "ipdb = memorious_extended.operations.debug:ipdb",
        # ],
    },
    extras_require={
        "dev": [
            "pytest",
            "pytest-env",
            "pytest-cov",
            "pytest-mock",
            "sphinx",
            "sphinx_rtd_theme",
            "recommonmark",
        ],
    },
)
