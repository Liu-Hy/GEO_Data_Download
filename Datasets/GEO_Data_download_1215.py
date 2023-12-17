from ftplib import FTP
import os
from Bio import Entrez
from urllib.parse import urlparse
import sys
sys.path.append('../')
from tools import utils
import traceback
import pandas as pd


# FTP链接信息

def download_files(ftp, remote_file_paths, local_file_paths):
    for remote_file_path, local_file_path in zip(remote_file_paths, local_file_paths):
        with open(local_file_path, 'wb') as file:
            ftp.retrbinary('RETR ' + remote_file_path, file.write)


def read_keywords():
    file_path = r"../Datasets/new_task.csv"
    # 读取 Excel 文件
    # data = pd.read_excel(file_path, sheet_name="traits")
    data = pd.read_csv(file_path)
    # 读取某一列的所有元素并放入列表
    traits = data['Trait'].tolist()

    return traits


def get_GEO_series_access(search_term):
    '''
    Use keywords to get related GEO data accessions
    :param search_term: keywords
    :return: GEO data accessions
    '''
    Entrez.email = "lujianrong@hust.edu.cn"
    Entrez.api_key = "ef253a2bffaa04ec739ec8261482b477bf08"
    query = f"(30:10000[Number of Samples]) AND (\"Homo sapiens\"[Organism]) AND ({search_term})"
    # 搜索GEO数据集
    # search_term = "cancer"  # 替换为您要搜索的关键字
    handle = Entrez.esearch(db="gds", retmax=35, term=query)  # Retrieve 35 records
    record_by_trait = Entrez.read(handle)
    print("record_by_trait", record_by_trait)
    handle.close()
    dataset_accessions = []
    Series_FTP_Links = []
    # print("IdList", len(record_by_trait["IdList"]))
    for idx, dataset_id in enumerate(record_by_trait["IdList"]):
        # dataset_id = record["IdList"][0]
        dataset_handle = Entrez.esummary(db="gds", id=dataset_id)
        dataset_summary = Entrez.read(dataset_handle)
        dataset_handle.close()
        # print(dataset_summary)
        # 获取数据集的访问号
        dataset_accession = dataset_summary[0]['Accession']
        dataset_accessions.append(dataset_accession)
        Series_FTP_Links.append(dataset_summary[0]['FTPLink'])
    num = len(Series_FTP_Links)
    print(f" {num} series found for the provided trait search term.")
    return dataset_accessions, Series_FTP_Links


def progress_hook(count, block_size, total_size):
    if total_size > 0:
        percent = int(count * block_size * 100 / total_size)
        if percent > 100:
            percent = 100
        if percent % 100 == 0:
            # if FLAG_0 or FLAG_1:
            print(f"Downloaded {percent}%")

    else:
        print("Download in progress")


def download_GEO_data(dataset_inf, key_word, keyword_idx, checkpoint):
    ftp_host = 'ftp.ncbi.nlm.nih.gov'
    # 连接到FTP服务器
    ftp = FTP(ftp_host, timeout=600)
    ftp.login()
    # ftp.timeout = 300
    dataset_accessions, Series_FTP_Links = dataset_inf
    Tools = utils.Tool()
    # local_dir = f'../Datasets/GEO/{keyword_idx + 1}_{Tools.clean_filename(key_word)}'
    local_dir = f'/media/techt/DATA/GEO/{keyword_idx + 1}_{Tools.clean_filename(key_word)}'
    print("local_dir:", local_dir)

    if not os.path.exists(local_dir):
        os.makedirs(local_dir)
    print("Series_FTP_Links", Series_FTP_Links)
    Series_num = len(Series_FTP_Links)
    for i, Series_FTP_Link in enumerate(Series_FTP_Links):
        if i < checkpoint: continue
        # else: checkpoint=0
        try:
            print("Series_FTP_Link", Series_FTP_Link)
            # 解析FTP链接
            parsed_url = urlparse(Series_FTP_Link)
            # 提取ftp_host和ftp_path
            # ftp_host = parsed_url.netloc
            ftp_path = parsed_url.path
            ftp_link = f'ftp://{ftp_host}{ftp_path}'
            print("ftp_host:", ftp_host)
            print("ftp_path:", ftp_path)

            # 切换到目标路径
            ftp.cwd(ftp_path)

            # 获取文件列表
            file_list = ftp.nlst()
            print("file_list1", file_list)

            matrix_flag = False
            family_flag = False
            for file_name in file_list:
                if "matrix" in file_name:
                    matrix_flag = True
                if "soft" in file_name:
                    family_flag = True
            if matrix_flag == False: continue
            if family_flag == False: continue
            ftp.cwd(f'{ftp_path}matrix/')
            matrix_file_list2 = ftp.nlst()
            print("matrix", matrix_file_list2)
            matrix_file_urls = []
            matrix_file_names = []
            for filename2 in matrix_file_list2:
                if 'matrix' in filename2 and 'xml' not in filename2:
                    # print("filename2",filename2)
                    ftp.sendcmd("TYPE I")
                    matrix_file_size = ftp.size(filename2)
                    print("matrix_file_size (KB)", matrix_file_size / 1024)
                    if matrix_file_size / 1024 > 100 and matrix_file_size / 1024 < 102400:  # download file with size range: [100KB,100MB]
                        print(f"matrix_file {filename2} is available\n")
                        matrix_file_url = f'{ftp_path}matrix/{filename2}'
                        print("matrix_file_url", matrix_file_url)
                        matrix_file_urls.append(matrix_file_url)
                        matrix_file_names.append(filename2)

            ftp.cwd(f'{ftp_path}soft/')
            family_file_list2 = ftp.nlst()
            print("family", family_file_list2)
            family_file_urls = []
            family_file_names = []
            for filename2 in family_file_list2:
                if 'family' in filename2 and 'xml' not in filename2:
                    # print("filename2",filename2)
                    family_file_url = f'{ftp_path}soft/{filename2}'
                    print("family_file_url", family_file_url)
                    family_file_urls.append(family_file_url)
                    family_file_names.append(filename2)

            if len(family_file_urls) > 0 and len(matrix_file_urls) > 0:
                # 创建本地保存文件的目录
                local_dir_series = os.path.join(local_dir, dataset_accessions[i])
                if not os.path.exists(local_dir_series):
                    os.makedirs(local_dir_series)

                local_matrix_filenames = [os.path.join(local_dir_series, mfn) for mfn in matrix_file_names]
                download_files(ftp, remote_file_paths=matrix_file_urls, local_file_paths=local_matrix_filenames)

                local_family_filenames = [os.path.join(local_dir_series, ffn) for ffn in family_file_names]
                download_files(ftp, remote_file_paths=family_file_urls, local_file_paths=local_family_filenames)

                print(f"Downloaded: {matrix_file_names} and {family_file_names} for trait {key_word}\n")
            else:
                print(
                    f"No gene expression data exists in series {i} ({Series_num} series for trait {key_word} in total)) \n")
        except Exception as e:
            # 在异常发生时返回 i 和 idx 作为异常信息
            raise Exception((i, e))
    # 关闭FTP连接
    ftp.quit()
    # print("Download completed.\n")


if __name__ == '__main__':
    key_word = read_keywords()
    print(len(key_word))
    print(key_word)
    Tools = utils.Tool()
    last_checkpoint_i, last_checkpoint_j = Tools.check_point_read(
        path="../CheckPonits/GEO_data_download_CheckPoint.txt")
    try:
        for idx, keyword in enumerate(key_word):
            if idx < last_checkpoint_i: continue
            print("trait: ", keyword)
            data_info = get_GEO_series_access(search_term=keyword)
            download_GEO_data(dataset_inf=data_info, key_word=keyword, keyword_idx=idx, checkpoint=last_checkpoint_j)
            last_checkpoint_j == 0

    except Exception as e:
        print("An error occurred:", e)
        i = 0
        if len(e.args[0]) == 2:
            i, inner_error = e.args[0]
        else:
            inner_error = 'unknown'

        # 将当前的断点信息保存到文件中
        with open('../CheckPonits/GEO_data_download_CheckPoint.txt', 'w') as f:
            f.write(str(idx) + ";" + str(i))  # 保存最后一个完成的外层循环的索引
        print("checkpoint", str(idx) + ";" + str(i))
        print("keyword", keyword)
        print('运行中断，保存断点信息.')
        print(inner_error)
        traceback.print_exc()
