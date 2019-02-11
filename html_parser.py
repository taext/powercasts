#!/home/dd/anaconda3/bin/python
# HTML formatting tool for powercasts output files
import sys

def url_list_to_htm(link_list, filename=False):
    """takes list of urls, optionally filename to write to, 
    returns numbered HTML links"""
    
    links = []
    for i, line in enumerate(link_list):
        url = line.strip()
        # build HTML link string
        html = '#' + str(i) + ' ' + '<a href="' + url + '">' + url + '</a>'
        links.append(html)
    
    if filename:
        with open(filename, 'w') as f:
            for line in links:
                f.write(line)
                f.write(" <br> ")             
        print('Wrote file ' + filename)

    return(links)


def read_file_to_list(filename):
    """read content of file into list (internal)"""

    with open(filename, 'r') as f:
        content = f.readlines()
    return(content)


if __name__ == '__main__':
    # check for number of arguments
    if len(sys.argv) > 3:
        file_content = read_file_to_list(sys.argv[1])
        result = url_list_to_htm(file_content, sys.argv[2])

    else:
        print('mandatory arguments [filename to read] [filename to write]')