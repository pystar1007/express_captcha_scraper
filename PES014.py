"""
Welcome to NeuroLake Hydra! This is a simple query template for you to play and develop!
This little piece of code has one job, access a website on the internet and collect data.

You must implement all your code inside the 'query_execution' method. It will receive a dictionary
called 'input_data' containing the input to be used by the query and another dictionary
called 'properties' with some useful tools and information about how we want you to build the Hydra query.

"""
"""
<#@#HydraMetadata#@#>
{"version":"0.1.0",
"requirements":[],
"developer_contact":"equipe.neurolake@neurotech.com.br",
"host": "http://tracking.totalexpress.com.br/tracking/0",
"timeout":"15",
"selenium_usage":"true",
"query_name":"PES014"}
</#@#HydraMetadata#@#>
"""
""" NeuroLake imports """
# from utils.HydraBase import hydra_query, hydra_tester
# import utils.Lake_Exceptions as Exceptions
# import utils.Lake_Enum as Enums
import requests
import lxml.html
import urllib
try:
    import Image
except ImportError:
    from PIL import Image
import pytesseract
import cv2

"""You should need at least these imports"""
import json
import time
import sys
import os
import json
"""Your own imports go down here"""


properties = {
    "start_url": "http://tracking.totalexpress.com.br/tracking/0?cpf_cnpj",
    "captcha_url": "http://tracking.totalexpress.com.br/images/imagem_verifica.php",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
    "content_type": "application/x-www-form-urlencoded",
    "submit_url": "http://tracking.totalexpress.com.br/tracking/0",
    "tracking_data_url": "http://tracking.totalexpress.com.br/tracking_encomenda.php?code="
}
# @hydra_query
def request(input_data, properties):
    """request method
    :param: input_data: Dictionary containing all the content to be searched in the data sources
    :param: properties: Dictionaty containing execution properties such as selenium webdriver, Proxy configurations, IP configurations etc.
    :type input_data: dict
    :type properties: dict
    :returns: dictionary containing the result of the query parsing"""

    query_result = {
        "found_packages": False,
        "total_packages": 0,
        "packages": []
    }

    request_session = requests.session()
    
    name = input_data.get("name")
    cpf = input_data.get("cpf")
    cep = input_data.get("cep")

    try:
        i = 0
        while True:
            request_session.headers['User-Agent'] = properties['user_agent']
            response = request_session.get(str(properties['start_url']))
            if response.status_code == 200:
                break
            else:
                time.sleep(0.5)
                if i == 20: break
                i = i + 1
    except Exception as e:
        raise(e)

    k = 0
    while True:
        result = get_capcha_string(properties['captcha_url'], request_session)
        if result:
            try:
                if len(result) == 5:
                    int(result)
                    break
                else:
                    continue
            except ValueError:
                continue
        else:
            k = k + 1
            if k == 20:
                print("Failed get CAPTCHA code, I'll restart after 5 seconds")
                time.sleep(5)
                test_request(properties)
                return query_result
    
    print("captcha: ", result)

    request_payload = {
        "nome_razao": name,
        "cpf_cnpj" : cpf,
        "cep" : cep,
        "verificador": result,
        "action": "pesquisar"
    }

    headers = {
        'Accept-Language': 'en-US,en;q=0.9,pt-BR,es',
    }
    request_session.headers = headers

    count = 0
    while True:
        try:
            i = 0
            while True:
                form_submit_response = request_session.post(properties['submit_url'], data=request_payload)
                if form_submit_response.status_code == 200:
                    response_html = lxml.html.fromstring(form_submit_response.content)
                    break
                else:
                    if i == 20: 
                        print("Can not access to: ", properties['submit_url'])
                        sys.exit(0)
                    i = i + 1
        except Exception as e:
            print(e)
            sys.exit(0)

        if "Ver Detalhes" in form_submit_response.text:
            print("Form submit success!")
            break
        else:
            error_message = response_html.xpath('//span[@class="erro"]/text()')
            print("Error Message: ", error_message[0])
            count = count + 1
            if count == 3:
                return query_result
            else:
                continue

    data_codes = response_html.xpath('//tr/@onclick')
    package_ids = response_html.xpath('//tr/td[1]/text()')
    i = 0
    for code in data_codes:
        temp = {}
        k = 0
        res = request_session.get(properties['tracking_data_url'] + code.split("'")[1])

        if res.status_code == 200:
            query_result['found_packages'] = True
            temp.update({"delivery_date": "10/10/2016"})
            temp.update({"package_id" : package_ids[i]})
            temp.update({ "status_list" : []})

            i = i + 1
            tree = lxml.html.fromstring(res.text)
            rows = tree.xpath('//tr/td/font/text()')
            for row in rows:
                data = row.strip()
                if len(data) > 0:
                    k = k + 1
                    m = k % 3
                    if m == 1:
                        temp_dic = {}
                        temp_dic.update({"date": data})
                    if m == 0:
                        temp_dic.update({"status": data})
                        temp['status_list'].append(temp_dic)
            query_result['packages'].append(temp)
        else:
            print("Response Code:", res.status_code)
        
    query_result['total_packages'] = i
    print("Success")
    return query_result


def get_capcha_string(url, request_session):
    try:
        response = request_session.get(url)
        origin_png = "catpchar.png"
        refined_png = "refine_captchar.png"
        with open(origin_png, 'wb') as f:
            f.write(response.content)
        time.sleep(0.5)
        image = cv2.imread(origin_png)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = image.shape
        for i in range(h):
            for j in range(w):
                if image[i, j] == 0:
                    image[i, j] = 255
                if image[i, j] > 80:
                    image[i, j] = 255

        image = cv2.blur(image, (3, 3))
        cv2.imwrite(refined_png, image)
        captchar_string = pytesseract.image_to_string(Image.open(refined_png))
        return captchar_string
    except Exception as e:
        print(e)
        return None

# @hydra_tester(__file__)
def test_request(my_test_properties):    
    # You can extend the properties from you file metadata
    try:
        result = request({"name":"Raony", "cpf":"06908488462", "cep":"50950005"}, my_test_properties)
    except Exception as e:
        raise(e)
    
    with open('my_result.json', 'w', encoding='utf-8') as json_file:  
        json.dump(result,json_file, ensure_ascii=False)
    assert type(result) == dict

    assert isinstance(result['found_packages'], bool)
    assert isinstance(result['total_packages'], int)
    assert isinstance(result['packages'], list)

    packages = result['packages'][0]

    assert isinstance(packages['delivery_date'], str)
    assert isinstance(packages['package_id'], str)
    assert isinstance(packages['status_list'], list)

    status = packages['status_list'][0]

    assert isinstance(status['date'], str)
    assert isinstance(status['status'], str)


if __name__=="__main__":
    test_request(properties)
