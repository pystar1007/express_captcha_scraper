"""
This module contains dictionaries and definitions of a variety of NeuroLake parameters

**environ_variables**:
    In the context of constructing a HydraQuery, this dictionary will provide you with all the
    environment variables existing in the operational system. Also, all the metadata you defined
    in your Hydra query file.

    :Usage:
        >>> import utils.Lake_Enum as Enums
        >>> query_name = Enums.environ_variables["query_name"]
        >>> target_host = Enums.environ_variables["host"]

**QUERY_VERSIONS**:
    This dictionary contains a the current version of your Hydra query. Your query version is defined
    automatically by our architecture during your query registration
    
    :Usage:
        >>> import utils.Lake_Enum as Enums
        >>> query_version = Enums.QUERY_VERSIONS[Enums.environ_variables["query_name"]]
        >>> print(f"query version: {query_version}")
        query version: 1.0.2
"""
import os

environ_variables = dict(os.environ)

SAVE_TARGETS = {"PARSER":"parser","SCRAPER":"scraper"}
EFS_ORIGINS = SAVE_TARGETS
EFS_ORIGINS['CRAWLER'] = EFS_ORIGINS['SCRAPER']

QUERY_VERSIONS = {}

Defaults = {"TIMESTAMP_FORMAT":'%Y-%m-%d--%H:%M:%S', "VERSION_SEPARATOR":"#@#"}