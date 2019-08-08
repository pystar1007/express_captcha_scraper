import json
import time
import sys

from . import Lake_Utils as Utils
from . import Lake_Exceptions as Exceptions
from . import Lake_Enum as Enums

def hydra_query(query):
    """
    This is the decorator responsible for orchestrating the correct execution of a hydra query.
    A set of verifications are performed in order to make sure the execution will follow as intended.

    :param query: The python function which will perform the query
    :type query: function

    :returns: python inner function

    :Example:

    >>> from utils.HydraBase import hydra_query
    >>> @hydra_query
    >>> def my_own_hydra_query(input_json, query_properties):
    >>>     return {"SUCCESS":True}
    >>> my_own_hydra_query({"arg1":"foo"},{"property1":"bar"})
    Execution Result: {"SUCCESS":true}

    .. warning:: The query function you provide MUST receive two dictionaries as input. The Hydra architecture will send one input dictionary containing the keys your query will execute and one property dictionary containing the artifacts your query need to execute in the Hydra environment for example, a working webdriver
    """
    def hydra_wrapper(input_data, properties):
        if not isinstance(input_data, dict):
            raise ValueError("You should provide input_data as a dict")
        if not isinstance(properties, dict):
            raise ValueError("You should provide properties as a dict")
        file_timestamp = time.strftime(Enums.Defaults["TIMESTAMP_FORMAT"])

        query_result = query(input_data, properties)
        print (f"Execution Result: {json.dumps(query_result)}")

        if not isinstance(query_result, dict):
            raise ValueError("Your query must return a dictionary to the Hydra architecture")
        query_name = Enums.environ_variables['query_name']
        query_info = {}
        query_info['query_name'] = query_name
        query_info['query_version'] = Enums.QUERY_VERSIONS[query_name]
        query_info['query_input'] = input_data
        query_info['query_date'] = time.strftime(Enums.Defaults['TIMESTAMP_FORMAT'])
        query_info['file_timestamp'] = file_timestamp
        query_info.update(query_result)
        Utils.save_data(Enums.SAVE_TARGETS['PARSER'],
                        query_info['query_name'],
                        file_timestamp,
                        Utils.generate_filename(list(input_data.values()),
                                                extension='json',
                                                status="SUCCESS",
                                                timestamp=file_timestamp),
                        query_info)
        return query_info
    return hydra_wrapper

def hydra_tester(query_file_name):
    """
    This decorator encapsulates the process of testing your query inside our architecture. It makes sure to 
    allow the testing environment to have the same conditionas as if your query would be executing in one of
    our hydra instances. 

    :param query_file_name: This is the path to the file containing your source code. The tester will load the hydra_meta_data present in the provided file and load the correct environment variables and execution artifacts acording to your meta data specification.
    :type query_file_name: str

    :returns: python inner function

    :Example:

    >>> from utils.HydraBase import hydra_tester
    >>> @hydra_tester(__file__) #This provides the current file's path to the hydra tester
    >>> def test_request(my_test_properties): # You must name this function as 'test_request'
    >>>     result = request({"cnpj":"05359081000134"}, my_test_properties)
    >>>     assert type(result) == dict
    
    .. warning:: The decorator will provide the test_request function with a dictionary "my_test_properties". This dictionary contains the properties for your execution and if you defined selenium_usage as "true" the dictionary will contain a working selenium webdriver instance.

    """
    def hydra_test_loader(test_function):
        my_test_properties = Utils.load_parameters(query_file_name)
        def tester_wrapper():
            test_function(my_test_properties)
        return tester_wrapper
    return hydra_test_loader