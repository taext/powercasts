#!/home/dd/anaconda3/bin/python
import re, requests, json, sys
from more_itertools import unique_everseen
from tqdm import tqdm


def main(ifilename):

    file_name = ifilename
    file_name_wo_end = file_name[:-4]
    f = open(file_name)
    file_content = f.read()

    m3 = re.findall('xmlUrl=\"(.+?)\"', file_content)
    m4 = re.findall('text=\"(.+?)\"', file_content)
    m4.pop(0)

    result = []
    for i in range(len(m4)):
        print(m4[i], m3[i])
        result.append((m4[i], m3[i]))


    rss_dict = {}
    for name, url in tqdm(result):
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:58.0) Gecko/20100101 Firefox/58.0'}, timeout=15)
        except:
            print("failed: " + url)
# imid, delete me
        rss_dict[name] = r.text
        tqdm.write('Downloaded ' + url + '\n')
    json_filename = file_name_wo_end + ".json"
    with open(json_filename,'w') as outfile:
        json.dump(rss_dict, outfile)


    all_urls_3 = []

    for content in rss_dict.values():
        m = re.findall('\"(http\S+?\.(?:mp3|mp4))[\"\?]', content, re.IGNORECASE)
        if m:
            for item in m:
                all_urls_3.append(item)

    txt_filename = file_name_wo_end + ".txt"
    f = open(txt_filename,'w')

    unique_urls = list(unique_everseen(all_urls_3))
    for url in unique_urls:
        f.write(url)
        f.write("\n")
    f.close()


if __name__ == '__main__':

    main(sys.argv[1])
