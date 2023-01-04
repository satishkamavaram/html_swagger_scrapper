import parsel 
import requests
from typing import Iterator


#URL= "https://10.122.41.160/docs/@cisco-bpa-platform/ms-script-runner/index.html"

def parse_html_table(table : parsel.selector.SelectorList ) -> Iterator[str]:
    param_key = None
    param_type = None
    mandatory = False
    for _, tr in enumerate(table.xpath(".//tr//td")):
        if param_key is None:
            param_key = tr.xpath(".//text()").get()
            if param_key is not None:
                param_key = param_key.strip()
               # print(param_key)
        if param_type is None:
            param_type = tr.xpath(".//div//div//div//span//text()").get()
            if param_type is not None:
                param_type = param_type.strip()
                #print(param_type)
        if param_key is not None and  len(param_key) >0 and param_type is not None and len(param_type) > 0:
            #print(type(param_key), param_key,len(param_key))
            #print(type(param_type),param_type, len(param_type))
            if param_key[-1] == '*':
                param_key = param_key[:-1]
                mandatory = True
            yield f'{apiName},{param_key},{mandatory},{param_type}\n'
            param_key = None
            param_type = None
            
response = requests.get(URL,verify=False).text
with open("bpa.html", 'w') as file:
    file.write(response)
selector = parsel.Selector(text=response)

path_params_list = []
query_params_list = []
with open("bpa_apis.csv", 'w') as file:
    file.write("apiName,apiDesc,http_method,uri")
    file.write('\n')
    for index, api_section in enumerate(selector.xpath("//div[@id='sections']//section//div")):
        apiDesc = api_section.xpath(".//article//div//h1//text()").get()
        apiName = api_section.xpath(".//article/@data-name").get()
        http_method = api_section.xpath(".//article//pre/@data-type").get()
        uri = api_section.xpath(".//article//pre//code//span//text()").get()
            
        if apiName is not None and http_method == 'get':
            #print(f'apiName: {apiName}, http_method: {http_method}, uri: {uri}, apiDesc: {apiDesc}\n')
            file.write(f'{apiName},{apiDesc},{http_method},{uri}\n')
            has_path_params = True if len(api_section.xpath(".//article//div[contains(.//text(), 'Path parameters')]")) > 0 else False
            has_query_params = True if len(api_section.xpath(".//article//div[contains(.//text(), 'Query parameters')]")) > 0 else False
            query_params_index = 2 if has_query_params and has_path_params else 1
            #print(f'{has_path_params} , {has_query_params} , {query_params_index}')
            article_path = api_section.xpath(".//article")
            if has_path_params:
                table = article_path.xpath("(.//table)[1]")
                for value in parse_html_table(table):
                    path_params_list.append(value)
            if has_query_params:
                table = article_path.xpath(f"(.//table)[{query_params_index}]")
                for value in parse_html_table(table):
                    query_params_list.append(value)

with open('path_params.csv', 'w') as file:
    file.write("apiName,path_param,mandatory,path_param_type")
    file.write('\n')
    for data in path_params_list:
         file.write(data) 

with open('query_params.csv', 'w') as file:
    file.write("apiName,query_param,mandatory,query_param_type")
    file.write('\n')
    for data in query_params_list:
         file.write(data)