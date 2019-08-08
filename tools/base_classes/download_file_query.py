import sys
import os
import time
import json
import shutil
from subprocess import check_call
from subprocess import Popen
from datetime import datetime
# import tools.base_classes.convert_file_query as FileConvert
# --------------------------------Neurolake Imports----------------------------------------------
import utils.Lake_Utils as Utils # Provide general methods used by most queries
import utils.Lake_Enum as Enums # Provide values and general information used by the architecture
import utils.Lake_Exceptions as Exceptions
class FileDownloaderException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class ExtractFileException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class FileDownloader():
    """Class made to abstract the File Downloading proccess to queries that need only to download files from servers
    This Class downloads the content directly to your hard drive following the correct structure defined in the Hydra standard. When you use this class, we guarantee that, when your query is executed in our architecture, we will correctly handle the processing and disponibilization of your file's content in our databases 
    
    :param target_url: Url from which the content will be downloaded
    :type target_url: str
    :param query_input: This is the dictonary your query received from the architecture containing the input data to be executed. We will use this to create the filename
    :type query_input: dict
    :param query_name: Codename of your query. Used to create the correct filename and acessible via :mod:`.Lake_Enum`
    :type query_name: str
    :param file_format: Format of the downloaded File. The default value is 'zip'.
    :type file_format: str
    :param wget_headers: (optional) We use `wget` to fetch the data. If you need, you can provide specific headers that will be passed down to `wget`
    :type wget_headers: dict
    :param efs_origin: (optional) We understand as `origin` the type of the data being saved. In this scenario, the only acceptable (an default) value is "SCRAPER"
    :type efs_origin: str
    """
    def __init__(self, target_url, query_name, query_input, file_format='zip', wget_headers=None, efs_origin='SCRAPER'):
        self.target_url = target_url
        self.query_name = query_name
        self.query_input = query_input
        self.file_format = file_format
        self.wget_headers = wget_headers
        self.efs_origin = efs_origin
        self.unsuported_formats = ['jpg', 'png', 'doc']

    def __send_file_to_s3__(self, file_path):
        return True
    def download_file(self, post_data=None, ref_date=False, send_s3=False):
        """Method to download a file directly to the hard drive. After you call this method, the resulting file will be avaliable at the root of the HydraSDK folder, however, if you downloaded a compressed file, you should call the :func:`extract_content`

        :param post_data: dictionary or string containing the post data to be sent. If you set this variable, wget will send a post request to the website
        :type post_data: dict

        :param ref_date: This tells the method to use ref date in the resulting filename. The ref_date is the date of reference for the query execution.
        :type ref_date: bool

        :param send_s3: Flag that defines if the data will be sent to S3. When the SDK is executing in your machine, this parameter is always False.
        :type send_s3: bool

        :returns: filename for the downloaded file
        :rtype: str

        :Example:
            >>> import tools.base_classes.download_file_query as DownloadTool
            >>> import utils.Lake_Enum as Enums
            >>> file_downloader = DownloadTool.FileDownloader(target_url=target_url, query_name=Enums.environ_variables['query_name'], query_input=input_data)
            >>> resulting_file = file_downloader.download_file()

        """
        file_timestamp = time.strftime(Enums.Defaults['TIMESTAMP_FORMAT'])
        print(file_timestamp)
        if self.wget_headers is not None:
            self.wget_headers['Connection'] = 'close'
        file_name = Utils.save_data(origin=Enums.EFS_ORIGINS[self.efs_origin],
                                    query_name=self.query_name,
                                    timestamp=file_timestamp,
                                    filename=Utils.generate_filename(list(self.query_input.values()),
                                                                     extension=self.file_format,
                                                                     status="SUCCESS",
                                                                     timestamp=file_timestamp,
                                                                     ref_date=ref_date),
                                    data=self.target_url,
                                    is_data_url=True,
                                    headers_dic=self.wget_headers,
                                    post_data=post_data)

        # Check if the file downloaded is valid
        if os.stat(file_name).st_size <= 100:
            try:
                os.remove(file_name)
            except OSError:
                pass
            raise FileDownloaderException("FileDownloader: Wget Downloaded an Empty File")

        elif send_s3:
            compressed_file = self.__send_file_to_s3__(file_name)
            os.remove(compressed_file)

        return file_name


    def get_timestamp_content(self, file_name):
        if self.file_format == 'zip':
            import zipfile
            file = zipfile.ZipFile(file_name, "r")
            timestamp = []
            for info in file.infolist():
                time_info = str(info.date_time[2])+'#@#'+\
                            str(info.date_time[1])+'#@#'+\
                            str(info.date_time[0])
                timestamp.append(time_info)
            return timestamp

        elif self.file_format == 'rar':
            import rarfile
            file = rarfile.RarFile(file_name, "r")
            timestamp = []
            for info in file.infolist():
                time_info = str(info.date_time[2]) + '#@#' + \
                            str(info.date_time[1]) + '#@#' + \
                            str(info.date_time[0])
                timestamp.append(time_info)
            return timestamp

    def extract_content(self, file_name, avoid_normalization=False, wanted_file='', codif='utf8', new_extension='csv'):
        """
        Extracts the given file to the default data location. This method will try its best to extract all the data from the compressed file downloaded by the :func:`download_file` method

        :param file_name: The name of the downloaded file. This is the returned value from the `download_file` method.
        :type file_name: str

        :param avoid_normalization: This tells the function to keep the file names as they are, without changing the content
        :type avoid_normalization: bool

        :param wanted_file: Use this if you have an unique file to be extracted from a compressed file containing multiple files
        :type wanted_file: str

        :param codif: Codification for the normalization tool. See :func:`.normalize_content` 
        :type codif: str

        :param new_extension: The extension for the extracted files (Default csv)
        :type new_extension: str

        :returns: None
        :rtype: None

        :Example:
            >>> import tools.base_classes.download_file_query as DownloadTool
            >>> import utils.Lake_Enum as Enums
            >>> file_downloader = DownloadTool.FileDownloader(target_url=target_url, query_name=Enums.environ_variables['query_name'], query_input=input_data)
            >>> resulting_file = file_downloader.download_file()
            >>> file_downloader.extract_content(resulting_file)
        """
        file_timestamp = time.strftime(Enums.Defaults['TIMESTAMP_FORMAT'])
        sep=Enums.Defaults['VERSION_SEPARATOR']
        if self.file_format == 'zip':
            temp_folder = file_name.replace('.zip', '')
            os.makedirs(temp_folder)
            try:
                os.system('unzip '+file_name+' -d '+temp_folder)
                file_list = []
                count=0
                for basedir, subdirs, files in os.walk(temp_folder):
                    if len(files) > 0:
                        for file_path in files:
                            file_list.append(os.path.join(basedir, file_path))

                for _file in file_list:
                    # Check if the extension is not allowed
                    extension = _file.split('.')[-1]
                    if extension not in self.unsuported_formats:
                        if extension == 'kmz':
                            file_name_no_extension = os.path.basename(_file).split('.')[0]
                            personal_timestamp = self.get_timestamp_content(file_name)
                            if avoid_normalization == False:
                                encoded = Utils.codec_removal(file_name_no_extension)
                            else:
                                encoded = file_name_no_extension
                            no_timestamp_list = file_name.split('#@#')
                            no_timestamp = '#@#'.join(no_timestamp_list[:-1])
                            new_file_name = no_timestamp+sep+encoded+sep+personal_timestamp[count]+sep+file_timestamp+\
                                            '.'+new_extension
                            Popen(['mv', _file, new_file_name]).wait()
                            count+=1
                        if extension == 'mdb':
                            data_ref_mdb = '01#@#01#@#' + file_name.replace('.zip', '').split('/')[8][:-23]
                            no_timestamp_list = file_name.split('#@#')
                            no_timestamp = '#@#'.join(no_timestamp_list[:-1])
                            first_file=no_timestamp+\
                                    sep+Utils.normalize_content(wanted_file, codif=codif)+ \
                                    sep+str(count)+sep+data_ref_mdb+sep+file_timestamp+'.'+new_extension
                            casco = open(first_file, "w")
                            first=Popen(['mdb-export', _file, wanted_file], stdout=casco)
                            first.wait()
                            if os.stat(first_file).st_size <= 0:
                                os.remove(first_file)
                            count += 1

                        elif extension in ['txt', 'csv'] and wanted_file in _file:
                            file_name_no_extension = os.path.basename(_file).split('.')[0]
                            personal_timestamp = self.get_timestamp_content(file_name)
                            if avoid_normalization == False:
                                encoded = Utils.normalize_content(file_name_no_extension, codif=codif)
                            else:
                                encoded = file_name_no_extension
                            no_timestamp_list = file_name.split('#@#')
                            no_timestamp = '#@#'.join(no_timestamp_list[:-1])
                            # Rename the file to standardized date
                            new_file_name = no_timestamp+sep+encoded+sep+ personal_timestamp[count]+sep+file_timestamp+\
                                            '.'+new_extension
                            Popen(['mv', _file, new_file_name]).wait()
                            count+=1
            except OSError:
                try:
                    os.remove(file_name)
                    shutil.rmtree(temp_folder)
                except OSError:
                    raise ExtractFileException("Couldn't remove zip file")
            finally:
                try:
                    os.remove(file_name)
                    shutil.rmtree(temp_folder)
                    #print 'a'
                except OSError:
                    pass


        elif self.file_format == 'rar':
            temp_folder = file_name.replace('.rar', '')
            os.makedirs(temp_folder)
            try:
                os.system('unrar ' + ' e ' + file_name + ' ' + temp_folder)
                file_list=[]
                count=0
                for basedir, subdirs, files in os.walk(temp_folder):
                    if len(files) > 0:
                        for file_path in files:
                            file_list.append(os.path.join(basedir, file_path))
                for _file in file_list:
                    # Check if the extension is not allowed
                    extension = _file.split('.')[-1]
                    if extension not in self.unsuported_formats:
                        if extension in ['txt', 'csv'] and wanted_file in _file:
                            file_name_no_extension = os.path.basename(_file).split('.')[0]
                            personal_timestamp = self.get_timestamp_content(file_name)
                            if avoid_normalization == False:
                                encoded = Utils.normalize_content(file_name_no_extension, codif=codif)
                            else:
                                encoded = file_name_no_extension
                            no_timestamp_list = file_name.split('#@#')
                            no_timestamp = '#@#'.join(no_timestamp_list[:-1])
                            new_file_name = no_timestamp+sep+encoded+sep+personal_timestamp[count]+sep+file_timestamp+\
                                            '.'+new_extension
                            Popen(['mv', _file, new_file_name]).wait()
                            count+=1
            except OSError:
                try:
                    os.remove(file_name)
                    shutil.rmtree(temp_folder)
                except OSError:
                    raise ExtractFileException("Couldn't remove rar file")
            finally:
                try:
                    os.remove(file_name)
                    shutil.rmtree(temp_folder)
                except OSError:
                    pass

