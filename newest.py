import json, re, sys

with open(sys.argv[1]) as infile:

    rss_dict = json.load(infile)

all_urls_3 = []

non_matches = []

for content in rss_dict.values():
    m = re.findall('\"(http\S+?\.(?:mp3|mp4))[\"\?]', content, re.IGNORECASE)
    if m:
        for item in m:
            all_urls_3.append(item)
            break
    else:
        non_matches.append(content)

[print(item) for item in all_urls_3]


# for i, item in enumerate(non_matches):
#     filename = str(i) + '_test.txt'
#     with open(filename,'w') as f:
#         f.write(non_matches[0])
