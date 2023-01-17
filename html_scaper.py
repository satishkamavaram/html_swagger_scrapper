import parsel 
import requests
from typing import Iterator, NamedTuple, Optional
import csv
import jsonpickle
import re
import os

URL= "swagger http url"

def extract_api():
    m = re.search('test-platform/(.+?)/index.html', URL)
    if m:
        return m.group(1)
       

BASE_FOlDER = extract_api()
os.makedirs(BASE_FOlDER,exist_ok=True)

_INTENT_TO_SLOTS = os.path.join(BASE_FOlDER,'intents_slots.json')
_INTENT_TO_INPUT = os.path.join(BASE_FOlDER,'intent_to_input.csv')
_INTENT_TO_OUTPUT = os.path.join(BASE_FOlDER,'intent_to_output.csv')
_BPA_APIS = os.path.join(BASE_FOlDER,'bpa_apis.csv')
_PATH_PARAMS = os.path.join(BASE_FOlDER,'path_params.csv')
_QUERY_PARAMS = os.path.join(BASE_FOlDER,'query_params.csv')
_BPA_RESPONSE = os.path.join(BASE_FOlDER,'bpa.html')
    
class Slot:
    def __init__(self,paramName:str,question:str,mandatory:bool,dataType:str,type:str,regexValidator:Optional[str],
                 validationFunction:Optional[str],defaultValue:Optional[any],listOfSupportedValues:Optional[list]=[]) -> None:
        self.paramName = paramName
        self.question = question
        self.validationFunction = validationFunction
        self.regexValidator = regexValidator
        self.listOfSupportedValues = listOfSupportedValues
        self.mandatory = mandatory
        self.defaultValue = defaultValue
        self.dataType    = dataType
        self.type = type
    
    
class Api:
     def __init__(self,intent:str,apiName:str,apiDesc:str,httpMethod:str,uri:str,slots:Optional[list[Slot]]=[]) -> None:
         self.intent = intent
         self.apiName = apiName
         self.apiDesc = apiDesc
         self.httpMethod = httpMethod
         self.uri = uri
         self.slots = slots
     
     
class Apis:
    def __init__(self,apis:list[Api]) -> None:
        self.apis = apis


class AdditionalInfo(NamedTuple):
    additionalInfo: str
    defaultValue: Optional[any]
    regexValidator: Optional[str]
    listOfSupportedValues: Optional[list]
    functionNameValidator: Optional[str]
    
_additional_info = dict()

with open('ms-script-runner.csv', mode='r') as infile:
    reader = csv.reader(infile)
    next(reader)
    for row in reader:
        _additional_info[row[0]] = AdditionalInfo(row[1] if row[1] is not None and len(row[1].strip())>0 else None,
                                                  row[2] if row[2] is not None and len(row[2].strip())>0 else None,
                                                  row[3] if row[3] is not None and len(row[3].strip())>0 else None,
                                                  row[4].split(",") if row[4] is not None and len(row[4].strip())>0 else [],
                                                  row[5] if row[5] is not None and len(row[5].strip())>0 else None)._asdict()
    print(_additional_info)
    
def parse_html_table(table : parsel.selector.SelectorList , type: str) -> Iterator[str]:
    param_key = None
    param_type = None
    mandatory = False
    for _, tr in enumerate(table.xpath(".//tr//td")):
        if param_key is None:
            param_key = tr.xpath(".//text()").get()
            if param_key is not None:
                param_key = param_key.strip()
        if param_type is None:
            param_type = tr.xpath(".//div//div//div//span//text()").get()
            if param_type is not None:
                param_type = param_type.strip()
        if param_key is not None and  len(param_key) >0 and param_type is not None and len(param_type) > 0:
            if param_key[-1] == '*':
                param_key = param_key[:-1]
                mandatory = True
            yield f'{apiName},{param_key},{mandatory},{param_type}\n',Slot(paramName=param_key,
                                                                           question=f'Please enter {param_key}('+ _additional_info[param_key]['additionalInfo'] if param_key in _additional_info else ""+')',
                                                                           mandatory=mandatory,
                                                                           dataType=param_type,
                                                                           type=type,
                                                                           listOfSupportedValues = _additional_info[param_key]['listOfSupportedValues'] if param_key in _additional_info  else [],
                                                                           regexValidator = _additional_info[param_key]['regexValidator'] if param_key in _additional_info  else None,
                                                                           validationFunction= _additional_info[param_key]['functionNameValidator'] if param_key in _additional_info  else None,
                                                                           defaultValue= _additional_info[param_key]['defaultValue'] if param_key in _additional_info  else None )
            param_key = None
            param_type = None
            
response = requests.get(URL,verify=False).text


with open(_BPA_RESPONSE, 'w') as file:
    file.write(response)
selector = parsel.Selector(text=response)

path_params_list = []
query_params_list = []
input_to_intent = []
intent_to_output = []
api_list = []
intents_json = None

with open(_BPA_APIS, 'w') as file:
    file.write("apiName,apiDesc,http_method,uri")
    file.write('\n')
    
    apis : list[Api] = []
    for index, api_section in enumerate(selector.xpath("//div[@id='sections']//section//div")):
        apiDesc = api_section.xpath(".//article//div//h1//text()").get()
        apiName = api_section.xpath(".//article/@data-name").get()
        http_method = api_section.xpath(".//article//pre/@data-type").get()
        uri = api_section.xpath(".//article//pre//code//span//text()").get()
        
        if apiName is not None and http_method == 'get':
            api_list.append(apiName)
            file.write(f'{apiName},{apiDesc},{http_method},{uri}\n')
            lowercase_intent = apiName.lower().replace('/', '').replace('<', '').replace('>', '')
            api = Api(intent=lowercase_intent,apiName=apiName,apiDesc=apiDesc,httpMethod=http_method,uri=uri,slots=[])
            apis.append(api)
            input_to_intent.append(f'{lowercase_intent},{apiName}\n')
            input_to_intent.append(f'{lowercase_intent},{apiDesc}\n')
            input_to_intent.append(f'{lowercase_intent},{"".join(apiDesc.split())}\n')
            has_path_params = True if len(api_section.xpath(".//article//div[contains(.//text(), 'Path parameters')]")) > 0 else False
            has_query_params = True if len(api_section.xpath(".//article//div[contains(.//text(), 'Query parameters')]")) > 0 else False
            query_params_index = 2 if has_query_params and has_path_params else 1
            article_path = api_section.xpath(".//article")
            if has_path_params:
                table = article_path.xpath("(.//table)[1]")
                for csv_value, slot_value in parse_html_table(table,'path_param'):
                    path_params_list.append(csv_value)
                    api.slots.append(slot_value)
            if has_query_params:
                table = article_path.xpath(f"(.//table)[{query_params_index}]")
                for csv_value, slot_value in parse_html_table(table,'query_param'):
                    query_params_list.append(csv_value)
                    api.slots.append(slot_value)
            has_slots =  True if len(api.slots) > 0 else False
            intent_to_output.append(f'{lowercase_intent},,{has_slots},api\n')
    bpa_apis = Apis(apis=apis)
    jsonpickle.set_encoder_options('json', indent=4) # sort_keys=True, indent=4)
    intents_json =jsonpickle.encode(bpa_apis,unpicklable=False)




with open(_INTENT_TO_SLOTS, 'w') as file:
    file.write(intents_json)
         
with open(_PATH_PARAMS, 'w') as file:
    file.write("apiName,path_param,mandatory,path_param_type")
    file.write('\n')
    for data in path_params_list:
         file.write(data) 

with open(_QUERY_PARAMS, 'w') as file:
    file.write("apiName,query_param,mandatory,query_param_type")
    file.write('\n')
    for data in query_params_list:
         file.write(data)
         
with open(_INTENT_TO_INPUT, 'w') as file:
    file.write("intent,utterance")
    file.write('\n')
    for data in input_to_intent:
         file.write(data)
    file.write('api,api')
        
with open(_INTENT_TO_OUTPUT, 'w') as file:
    file.write("intent,output,has_slots,next_intent")
    file.write('\n')
    for data in intent_to_output:
         file.write(data)
    apis = ",".join(api_list)
    file.write('api,"'+apis+'",False,')