import json, re, sys

with open(sys.argv[1]) as infile:

    rss_dict = json.load(infile)

all_urls_3 = []

for content in rss_dict.values():
    m = re.findall('\"(http\S+?\.(?:mp3|MP3))\"', content)
    for item in m:
        if '>' not in item:
            if '&' not in item:
                all_urls_3.append(item)
                break
"""
    txt_filename = file_name_wo_end + ".txt"
    f = open(txt_filename,'w')

    for url in all_urls_3:
        f.write(url)
        f.write("\n")
    f.close()

"""

[print(item) for item in all_urls_3]