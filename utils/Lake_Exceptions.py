class CriticalErrorException(Exception):
    """
    Hydra Exception responsible for exposing when any error that it is not defined in this documentation happens

    :Usage:
        >>> import utils.Lake_Exceptions as Exceptions
        >>> # An Error that we did not expect occurred 
        >>> raise Exceptions.CriticalErrorException("Provide any information that may help we identify the errro")
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class BlockException(Exception):
    """
    Hydra Exception responsible for exposing when any type of blocking occurrs. 
    
    :Blocking Situations: 
        We define that the query execution was "blocked" when the host took any measure to block the query access to the page content. A "blocking" situation could be:

         - An abnormally long response time
         - An specific message like "Limit Exceeded"
         - A blank response
         - A captcha challenge 

    :Usage:
        >>> import utils.Lake_Exceptions as Exceptions
        >>> raise Exceptions.BlockException("Provide any information that may help we identify the errro")
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class HttpTimeoutException(Exception):
    """
    Hydra Exception responsible for exposing when any operation inside the query takes too much time to execute

    :Possible Timeout Situations:
        - When the page takes too long to response and this is not configured as a :func:`BlockException`
        - When using any browser automation tool, if an operation depending on an element takes too long

    :Usage:
        >>> import utils.Lake_Exceptions as Exceptions
        >>> raise Exceptions.HttpTimeoutException("Provide any information that may help we identify the errro")
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class UnexpectedResultException(Exception):
    """
    Hydra Exception responsible for exposing when the query receives an unexpected result. Use this to sinalize 
    when, for example, the HTML page returned by the host is different from what you expected. This is **essential** for 
    sinalizing the need to update the query code

    :Usage:
        >>> import utils.Lake_Exceptions as Exceptions
        >>> import utils.Lake_Enums as Enums
        >>> page_source = driver.get(Enums.environ_variables["host"])
        >>> # Oh no! The page source is different and it is not a blocking situation!
        >>> raise Exceptions.UnexpectedResultException("Provide any information that may help we identify the errro")
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
