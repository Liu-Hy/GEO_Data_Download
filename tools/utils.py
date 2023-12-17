import json
import re
import openai
import PyPDF2
import tiktoken
import os

#openai.api_key = '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'
# 目前需要设置代理才可以访问 api
#os.environ["HTTP_PROXY"] = "127.0.0.1:8001"
#os.environ["HTTPS_PROXY"] = "127.0.0.1:8001"
class Tool:

     def is_question(self, s):
        """判断字符串是否是问题"""
        return s.strip().endswith("?")

     def readjson(self,filename):
         # 读取
         with open(filename, 'r', encoding='utf-8') as f:
             content = f.read()
             msgs = json.loads(content) if len(content) > 0 else {}
         return msgs
     def save_question_to_file(self, question, file_path):
        """保存问题到指定位置"""
        with open(file_path, 'a') as file:
            file.write(question + "\n")
     def save_api_key(self,a,file_path):
        b = json.dumps(a)
        f2 = open('file_path', 'w')
        f2.write(b)
        f2.close()
     def save_dict_to_txt(self,data, file_path,way):
         with open(file_path, way) as file:
             for key, value in data.items():
                 try:
                     file.write(f"{key}: {value}\n")
                 except Exception as e:
                     print(f"An error occurred while writing '{key}' with value '{value}': {str(e)}")

     def replace_slash_with_or(self,input_str):
        if "/" in input_str:
            # 如果字符串中存在"/"，则替换为"or"
            output_str = input_str.replace("/", "or")
        else:
            # 如果字符串中不存在"/"，则保持原样
            output_str = input_str
        return output_str
     def is_char_in_string(self,my_string, target_char):
        if target_char in my_string:
            print(f"The character '{target_char}' is present in the string.")
        else:
            print(f"The character '{target_char}' is not present in the string.")
        return target_char in my_string
     def has_character_after_number(self,input_string, character):
        # 遍历字符串中的每个字符（除了最后一个字符）
        for i in range(len(input_string) - 1):
            # 检查当前字符是否为数字，并且下一个字符是否为目标字符
            if input_string[i].isdigit() and input_string[i + 1] == character:
                return True
        return False
     def clean_filename(self, filename):
        # Define a regular expression to match unsupported characters
        pattern = r'[\\/:\*\?"<>\|\r\n\t ]+'  # Matches \ / : * ? " < > | \r \n \t
        cleaned_filename = re.sub(pattern, '-', filename)
        return cleaned_filename
     def check_point_read(self,path):
         try:
             with open(path, 'r') as f:
                 checkpoint = f.read()
                 last_checkpoint_i, last_checkpoint_j = checkpoint.strip().split(";")
                 last_checkpoint_i = int(last_checkpoint_i)
                 last_checkpoint_j = int(last_checkpoint_j)
         except FileNotFoundError:
             last_checkpoint_i = 0
             last_checkpoint_j = 0
         print(f"Check point start:i = {last_checkpoint_i} and j = {last_checkpoint_j}")
         return last_checkpoint_i,last_checkpoint_j

     def extract_lines_starting_with_digits(self,text):
         pattern = r'\d+[^a-zA-Z0-9\s]\s*(.*?)\n'
         matches = re.findall(pattern, text, re.MULTILINE)
         return [match.strip() for match in matches]
     # 读取PDF文件，并将内容存储为文本字符串

     def read_pdf(self,pdf_file):
        with open(pdf_file, "rb") as file:
            pdf_reader = PyPDF2.PdfFileReader(file)
            text = ""
            for page_num in range(pdf_reader.getNumPages()):
                page = pdf_reader.getPage(page_num)
                text += page.extractText()
        return text

     def num_tokens_from_messages(self,messages, model="gpt-3.5-turbo-0613"):
         """Returns the number of tokens used by a list of messages."""
         messages = [
             {"role": "system",
              "content": messages}
         ]
         try:
             encoding = tiktoken.encoding_for_model(model)
         except KeyError:
             encoding = tiktoken.get_encoding("cl100k_base")
         if model == "gpt-3.5-turbo-0613":  # note: future models may deviate from this
             num_tokens = 0
             for message in messages:
                 num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
                 for key, value in message.items():
                     num_tokens += len(encoding.encode(value))
                     if key == "name":  # if there's a name, the role is omitted
                         num_tokens += -1  # role is always required and always 1 token
             num_tokens += 2  # every reply is primed with <im_start>assistant
             return num_tokens
         else:
             raise NotImplementedError(f"""num_tokens_from_messages() is not presently implemented for model {model}.
       See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens.""")
     def split_text_into_paragraphs(self, text, max_tokens_per_paragraph=400):
        paragraphs = text.split('\n')  # 假设每段之间是用两个换行分隔的
        token_count = 0
        current_paragraph = ""
        result = []

        for paragraph in paragraphs:
            # 估算当前段落的 tokens 数量
            paragraph_tokens = self.num_tokens_from_messages(paragraph)
            # print(paragraph_tokens)

            # 如果当前段落加上当前段落的 tokens 数量不超过最大限制，则添加到当前段落中
            if token_count + paragraph_tokens <= max_tokens_per_paragraph:
                current_paragraph += paragraph + "\n\n"
                token_count += paragraph_tokens
            else:
                # 将当前段落添加到结果中，重置当前段落和 token 计数
                result.append(current_paragraph.strip())
                current_paragraph = paragraph + "\n\n"
                token_count = paragraph_tokens

        # 将最后一个段落添加到结果中
        if current_paragraph:
            result.append(current_paragraph.strip())

        return result

     def extract_number(self,s):
            # 从字符串中提取数字作为关键字
            num = ''
            for char in s:
                if char.isdigit():
                    num += char
                elif num:
                    break
            return int(num) if num else None

     def custom_sort(self,strings):
            # 自定义排序函数，根据提取的数字关键字进行排序
            return sorted(strings, key=self.extract_number)


