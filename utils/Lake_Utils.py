import time
import string
import random
import urllib.request, urllib.error, urllib.parse
import re #regular expression library
from datetime import datetime
import os
import subprocess
import json
import hashlib
from unicodedata import normalize
import bz2
import base64
import lxml
from lxml.html.clean import Cleaner
from selenium import webdriver

from . import Lake_Exceptions as Exceptions
from . import Lake_Enum as Enums


def random_identifier(size=5):
    """
    We provide a method for creating random identifiers used internally in our architecture. This identifier follows our development standards

    :param size: The size of the desired random identifier
    :type size: str

    :returns: a random string consisting of 'size' letters from a-z and numbers from 0-9
    """
    return''.join(random.choice(string.lowercase + ''.join([str(x) for x in range(10)])) for x in range(size))


def __convert_object_to_serializeable__(target_object):
    if isinstance(target_object, dict):
        for element in target_object.keys():
            if isinstance(target_object[element], bytes):
                target_object[element] = target_object[element].decode()
            elif isinstance(target_object[element], dict):
                temp_dict = target_object[element]
                for inner_element in temp_dict.keys():
                    temp_dict[inner_element] = __convert_object_to_serializeable__(temp_dict[inner_element])
            elif isinstance(target_object[element], datetime):
                target_object[element] = target_object[element].strftime("%Y-%m-%d:%H-%M-%S")
            elif isinstance(target_object[element], list):
                list_elements = []
                for list_element in target_object[element]:
                    list_elements.append(__convert_object_to_serializeable__(list_element))
                target_object[element] = list_elements

        return target_object

    elif isinstance(target_object, list):
        converted_list = []
        for element in target_object:
            converted_list.append(__convert_object_to_serializeable__(element))
        return converted_list
    
    elif isinstance(target_object, bytes):
        return target_object.decode()
    
    elif isinstance(target_object, datetime):
        return target_object.strftime("%Y-%m-%d:%H-%M-%S")
    
    else:
        return str(target_object)
    
def dump_dict_to_str(target_object):
    """This method provides an interface to convert python 3.6 dictionaries to JSON string.
    This is a workaround for the issue that occurs when we try to json.dumps() a dictionary
    containing a bytes element"""

    return json.dumps(__convert_object_to_serializeable__(target_object))


def extract_rendered_html(driver):
    """This method tries to execute all the javascripts from a webpage and returns the processed content as a HTML string. When using a selenium webdriver to scrape content from the internet, calling the `webdriver.page_source` returns only the page source. Sometimes this is not enought as we need the HTML with all the pages's javascript rendered.  
    
    :param driver: A Selenium webdriver instance with the page loaded
    :type driver: selenium.webdriver
    
    :returns: HTML string

    :Example:
        >>> import utils.Lake_Utils as Utils
        >>> my_webdriver_instance.get(target_page)
        >>> rendered_content = Utils.extract_rendered_html(my_webdriver_instance)
    
    """
    html = driver.execute_script("return document.getElementsByTagName('html')[0].innerHTML")
    return r'<html>'+html.encode('utf-8')+r'</html>'

def remove_accentuation(content, codif='utf-8'):
    """
    Removes all the accentuation from a given string

    :param content: Content which the accents must be removed
    :type content: str

    :param codif: Codification of the content
    :type codif: str

    :returns: Normalized string without accents
    """
    return normalize('NFKD', content).encode('ASCII', 'ignore').decode()

def normalize_content(content, codif='utf8'):
    """Remove any acentuation from the string and converts it to UPPERCASE.
    
    :param content: The content to be normalized
    :type content: str

    :param codif: The encoding of the string
    :type content: str

    :returns: Normalized uppercased string

    .. warning:: USE WITH CAUTION. Depending of the string encoding you may change the default codif parameter

    """
    try:
        return remove_accentuation(content, codif).upper()
    except UnicodeDecodeError as e:
        raise Exceptions.CriticalErrorException('utf-8 was not able to normalize this content: ( '+str(e)+') Maybe you should try to use encode_literal_utf_8_string method using other codification such as latin-1 or ISO-8859-1')


def compress_bz2(data):
    """
    Compresses your data using the bz2 library. We use Bz2 as our standard compressing format so, any data you save in your architecture is compressed before being sent.

    :param data: The content to be compressed
    :type data: str

    :returns: A string containing the compressed data
    """
    compressed = bz2.compress(data=data)
    return compressed

def save_data(origin, query_name, timestamp, filename, data, is_data_url=False, headers_dic=None, post_data=None, avoid_compression=False):
    """
    This is the main method used by our architecture to save data. We understand the concept of "saving data" as the process to store data to any sort of storage medium. This method is very different in our main architecture, and this simplified version works by saving you data to your local machine's hard drive.

    :param origin: We understand as `origin` the type of the data being saved. Your can specify `SCRAPER` or `PARSER` for this parameter. If you are saving raw HTML data, use `SCRAPER`, if you are saving JSON data, use `PARSER`
    :type origin: str

    :param query_name: The name of the running Hydra query.
    :type query_name: str

    :param timestamp: A timestamp following the Hydra standards. You can use the `Lake_Enum.Defaults['TIMESTAMP_FORMAT']` to provide a valid timestamp
    :type timestamp: str

    :param filename: The name for the file. Use the result of the :func:`.generate_filename` method here
    :type filename: str

    :param data: The data to be saved. If you are downloading a file, provide the url from which the method will fetch the data
    :type data: str

    :param is_data_url: This flag tells the method if the data is a url from where it will fetch the actual data to be saved
    :type is_data_url: bool

    :param headers_dic: We use `wget` to fetch the data. If you need, you can provide specific headers that will be passed down to `wget`
    :type headers_dic: dict

    :param post_data: Another conditional post data for the `wget` command.
    :type post_data: str

    :param avoid_compression: If you set this to `True`, any compression method used by our architecture will be avoided
    :type avoid_compression: bool

    :returns: The path to the saved file
    :rtype: str

    .. warning:: You shouldn't use this method during your query development. This is a **low level** method used by other methods of the architecture to save your data. If you are here trying to understand how to use our development kit to build your own hydra query, please refer to the :doc:`usage/quickstart` 

    """

    def get_headers(h):
        headers_string = ''
        if h is None:
            return ''
        for k in list(h.keys()):
            headers_string = headers_string + ' --header="' + str(k) + ': ' + str(h[k]) + '"'
        return headers_string

    if timestamp is None:
        date_time = datetime.now()
    else:
        date_time = datetime.strptime(timestamp, Enums.Defaults['TIMESTAMP_FORMAT'])
    filename =  './' + \
               origin + '/' + \
               query_name + '/' + \
               str(date_time.year) + '/' + \
               str(date_time.month) + '/' + \
               str(date_time.day) + '/' + \
               str(date_time.hour) + '/' + \
               filename

    try:
        os.makedirs(os.path.dirname(filename))
    except OSError as error:
        if 'File exists' in str(error) or '[Error 183]' in str(error):
            pass
        else:
            raise error
    finally:
        if is_data_url is False:
            if isinstance(data, bytes):
                open_mode = "wb"
            else:
                open_mode = "w"
            with open (filename, open_mode) as output_file:
                if type(data) == dict:
                    output_file.write(json.dumps(data))
                else:
                    output_file.write(data)
        else:
            if post_data is None:
                    post_command = ''
            else:
                if type(post_data) == str:
                    post_data_content = post_data
                elif type(post_data) == dict:
                    post_data_content = '&'.join(
                        [str(x[0]) + '=' + str(x[1]) for x in zip(list(post_data.keys()), list(post_data.values()))])
                else:
                    raise Exceptions.CriticalErrorException('Utils.save_data received a '+str(type(post_data))+'content when providing post_data parameter')
                post_command = ' --post-data '+post_data_content
            wget_command = 'wget ' + get_headers(headers_dic) + ' -x --output-document=' + str(filename) + ' "' + data +\
                            '"'+post_command
            return_value = os.system(wget_command)
            if not return_value == 0:
                if return_value == 1280:
                    wget_command = 'wget --no-check-certificate ' + get_headers(headers_dic) + ' -x --output-document=' + str(
                        filename) + ' "' + data + '"' + post_command
                    os.system(wget_command)
                else:
                    raise Exceptions.CriticalErrorException("Utils.save_data: Wget returned a status = "+str(return_value))
        return filename


def generate_filename(record_name=[], ref_date=False, extension="html", status="", timestamp=""):
    """ Generates a filename using the Hydra standards. This method is used by all our saving methods.

    :param record_name: A list containing all the names of the records being saved
    :type record_name: list
    :param ref_date: This tells the method to use ref date in the resulting filename
    :type ref_date: bool
    :param extension: The extension of the file being created
    :type extension: str
    :param status: The status of the execution. Usually our methods send SUCCESS here
    :type status: str
    :param timestamp: This is a string of the timestamp to be inserted in the filename. The timestamp helps ensure the filename uniquiness while providing some temporal information
    :type timestamp: str

    :returns: string containing the standardized filename 

    .. note:: This is an internal method used by our architecture for creating an uniform patterns for filenames and enrusing a good data flow, you should not concern yourself with this method
    """
    sep = Enums.Defaults['VERSION_SEPARATOR']
    record_name = [x for x in record_name]
    file_name = sep.join(record_name)
    file_name = file_name.replace(' ', '_')
    _timestamp = timestamp or time.strftime(Enums.Defaults['TIMESTAMP_FORMAT'])

    # Insercao de DATA_REF no nome antes do timestamp
    if ref_date is True:
        if extension in ['csv', 'pdf', 'ods']:
            if type(record_name) is list:
                for i in record_name:
                    try:
                        int(i)
                    except ValueError:
                        raise ValueError("There is a foreign element in the array")
                if len(record_name) == 2:
                    if len(record_name[0]) in [2, 1]:
                        month = record_name[0]
                        year = record_name[1]
                    else:
                        month = record_name[1]
                        year = record_name[0]
                    date_ref = '01#@#' + month + '#@#' + year
                if len(record_name) == 1:
                    date_ref = '01#@#01#@#' + record_name[0]

            elif type(record_name) is dict:
                date_ref = '01#@#' + record_name['month'] + '#@#' + record_name['year']
        return file_name + sep + status + sep + date_ref + sep + _timestamp + "." + extension
    else:
        return file_name + sep + status + sep + _timestamp + '.' + extension


def _get_datetime():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


def clean_html(html_text,
            javascript=True,
            scripts=True,
            style=True,
            embedded=True,
            links=True,
            forms=True,
            frames=True,
            comments=True,
            annoying_tags=True,
            meta=True,
            safe_attrs_only=True,
            remove_unknown_tags=True,
            processing_instructions=True
            ):
    """Clean all the javascript and styles from the HTML returning the string with only the html content. This methos is really usefull if you, by any means, need to save your HTML data or if you are encountering any problem in working with a javascript-heavy HTML. This method uses the `lxml.html.clean` module to clean the HTML 
    
    :param html_text: The HTML page content to be cleaned
    :type html_text: str 

    :param javascript: the javascript content will be removed from the HTML string
    :type javascript: bool

    :param scripts:  any <script> tags will be removed from the HTML string
    :type scripts: bool

    :param style: any style tags will be removed from the HTML string
    :type style: bool

    :param embedded: any embedded objects (flash, iframes) will be removed from the HTML string
    :type embedded: bool

    :param links: any <link> tags will be removed from the HTML string
    :type links: bool

    :param forms: any form tags will be removed from the HTML string
    :type forms: bool

    :param frames: any frame-related tags will be removed from the HTML string
    :type frames: bool

    :param comments: any comments will be removed from the HTML string
    :type comments: bool

    :param annoying_tags: tags that aren't wrong, but are annoying. <blink> and <marquee> will be removed from the HTML string
    :type annoying_tags: bool

    :param meta: any <meta> tags will be removed from the HTML string
    :type meta: bool

    :param safe_attrs_only: only include 'safe' attributes (specifically the list from the feedparser HTML sanitisation web site) will be left in the HTML string
    :type safe_attrs_only: bool

    :param remove_unknown_tags: any tags that aren't standard parts of HTML will be removed from the HTML string
    :type remove_unknown_tags: bool

    :param processing_instructions: any processing instructions will be removed from the HTML string
    :type processing_instructions: bool

    :returns: A cleaned string of HTML content

    .. note:: Some of these arguments are redundant and/or overlaping with others, you should fine tune the usage of the arguments for one that better suits your needs
    .. warning:: If you set `javascript` as `True`, you will not be able to perform any javascript execution in the HTML page so, use it with caution

    :Example:
        >>> import utils.Lake_Utils as Utils
        >>> my_webdriver_instance.get(target_host)
        >>> html_source = my_webdriver_instance.page_source
        >>> cleaned_html = Utils.clean_html(html_source)

    """
    # True = Remove | False = Keep
    cleaner = Cleaner()
    cleaner.javascript = javascript  # This is True because we want to activate the javascript filter
    cleaner.scripts = scripts  # This is True because we want to activate the scripts filter
    cleaner.style = style
    cleaner.embedded = embedded
    cleaner.links = links
    cleaner.forms = forms
    cleaner.frames = frames
    cleaner.comments = comments
    cleaner.page_structure = False # Keep page structure
    cleaner.annoying_tags = annoying_tags
    cleaner.meta = meta
    cleaner.safe_attrs_only = safe_attrs_only
    cleaner.remove_unknown_tags = remove_unknown_tags
    cleaner.processing_instructions = processing_instructions
    clean_content = cleaner.clean_html(lxml.html.fromstring(html_text))
    return lxml.html.tostring(clean_content)

def load_parameters(file_name):
    """
    This method loads all the contents from the HydraMetadata defined in your hydra query. Also, if you specified some directives like "selenium_usage", the architecture will provide you with a working selenium webdriver. The key_values provided in your query metadata will be avaliable at the Lake_Enum.environ_variables dictionary (:mod:`.Lake_Enum`).

    :param file_name: The name of the Hydra query. This method will open the file and load the `<#@#HydraMetadata#@#>` section in the begining of the file.
    :type file_name: str

    :returns: A dictionary containing the execution properties for your query and, if needed, a working webdriver.

    .. note:: This method is used internally by our architecture when your query is being tested in order to simulate our architecture standard behavior. You don't need to worry about it nor use it in your query implementation. Just make sure to use the correct decorators :func:`.hydra_query` and :func:`.hydra_tester`
    """
    full_path = os.path.realpath(file_name)

    with open(full_path,'r') as query_file:
        hydra_query_trimmed = query_file.read().replace('\n','')
        start_metadata = hydra_query_trimmed.find('<#@#HydraMetadata#@#>')+len('<#@#HydraMetadata#@#>')
        end_metadata = hydra_query_trimmed.find('</#@#HydraMetadata#@#>')

        try:
            hydra_metadata = json.loads(hydra_query_trimmed[start_metadata:end_metadata])
        except ValueError as error:
            raise Exception('Please provide a file with a correct HydraMetaData')
        
        Enums.environ_variables.update(hydra_metadata)

        Enums.QUERY_VERSIONS.update({hydra_metadata['query_name']:hydra_metadata['version']})

        # building input data and properties to pass down to the query
        query_properties = {"timeout":int(Enums.environ_variables['timeout'])}

        if Enums.environ_variables['selenium_usage'] == "true":
            from selenium.webdriver.chrome.options import Options
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            if ('chromedriver' in os.listdir('/usr/local/bin')) or ('chromedriver' in os.listdir('/usr/local/bin')):
                driver = webdriver.Chrome(options=chrome_options)
                query_properties['driver'] = driver
            elif os.path.isfile('./chromedriver'):
                driver = webdriver.Chrome(executable_path='./chromedriver',options=chrome_options)
                query_properties['driver'] = driver
            else:
                raise Exception("CHROME DRIVER NOT FOUND: Please download the chromedriver and place it on the hydra root directory")

        return query_properties