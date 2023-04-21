# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

version = "1.0.0"

setup(
    name="senaite.sqlmultiplex",
    version=version,
    description="SQL Multiplexer add-on for SENAITE",
    long_description=open("README.rst").read(),
    # long_description_content_type="text/markdown",
    # Get more strings from
    # http://pypi.python.org/pypi?:action=list_classifiers
    classifiers=[
        "Framework :: Plone",
        "Framework :: Zope2",
        "Programming Language :: Python",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
    ],
    keywords=["senaite", "lims", "opensource"],
    author="RIDING BYTES & NARALABS",
    author_email="senaite@senaite.com",
    url="https://github.com/senaite/senaite.sqlmultiplex",
    license="GPLv2",
    packages=find_packages("src", exclude=["ez_setup"]),
    package_dir={"": "src"},
    namespace_packages=["senaite"],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "senaite.lims>=1.3.5",
        "senaite.lims<2.0.0",
        # mysql-connector-python >= 8.0.24 does not support Python 2.x anymore
        # https://dev.mysql.com/doc/relnotes/connector-python/en/news-8-0-24.html
        "mysql-connector-python<8.0.24",
        # protobuf >= 3.18 does not support Python 2.7 anymore
        # https://groups.google.com/g/protobuf/c/A2p2IgHPIZc
        # https://github.com/protocolbuffers/protobuf/releases/tag/v3.17.3
        "protobuf==3.17.3",
        "collective.indexing",
    ],
    extras_require={
        "test": [
            "plone.app.testing",
            "unittest2",
        ]
    },
    entry_points="""
      # -*- Entry points: -*-
      [z3c.autoinclude.plugin]
      target = plone
      """,
)
