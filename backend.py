from ConfigParser import ConfigParser
from base64 import b64encode
from ftplib import FTP
import ftplib
import json
import os
import re
from urllib import urlopen
from urlparse import urlparse, urlunsplit
from bs4 import BeautifulSoup, Tag
import requests
import sys


config = ConfigParser()
config.read(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                         'config.ini'))


def parse(url, **kwargs):
    """Parse the HTML page and return a tuple of the formatted content and the
    local file links.

    :param url: The path to the HTML page.
    :type url: str.
    :param kwargs:
    :return: tuple -- the page content as a str and local file links as a list
    of str
    """
    soup = BeautifulSoup(urlopen(url))

    # Special thing for http://andersj.se
    if kwargs.get('remove_new_window_link', False):
        page = url.split('/')[-1]
        for a in soup.find_all('a'):
            if page == a['href']:
                p = a.parent.parent.parent.parent
                p.parent.contents.remove(p)

    if 'delete_links' in kwargs:
        links = soup.find_all('a')
        for page_to_delete in [x.strip() for x in
                               kwargs['delete_links'].split(',')]:
            for link in links:
                filename = os.path.basename(link['href'])
                if filename == page_to_delete:
                    link.parent.parent.contents.remove(link.parent)

    # Update file urls
    files = []
    for img in soup.find_all('img'):
        src = img['src']
        img['style'] = 'width: {}px; height: {}px;'.format(img['width'],
                                                           img['height'])
        img['src'] = os.path.join(config.get('wordpress', 'url'),
                                  'wp-content/uploads/old_site/{}'.format(
                                      img['src']))
        files.append({'old': src, 'new': img['src']})
    for a in soup.find_all('a'):
        old = a['href']
        if old.split('.')[-1] != 'pdf':
            continue
        a['href'] = os.path.join(config.get('wordpress', 'url'),
                                 'wp-content/uploads/old_site/{}'.format(
                                     a['href']))
        files.append({'old': old, 'new': a['href']})

    # Get the content inside the body tag and the js scripts
    body_content = ''.join(
        [unicode(x) for x in soup.body.contents if type(x) == Tag])
    scripts = soup.head.find_all('script')

    # Put the body content and scripts together
    content = u'\n'.join([unicode(x) for x in scripts])
    content = unicode(content) + unicode(body_content)
    content = u'[raw]<div class="old_site">{}</div>[/raw]'.format(content)
    content = BeautifulSoup(content).prettify()
    # Remove redundant br closing tags
    content = re.sub(r'</br>', '', content)

    return content, files


def get_tmp_directory_path():
    """Get the path to the tmp dir.

    Creates the tmp dir if it doesn't already exists in this file's dir.

    :return: str -- abs path to the tmp dir
    """
    tmp_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 'tmp')
    if not os.path.exists(tmp_directory):
        os.mkdir(tmp_directory)
    return tmp_directory


def download_files(url, files):
    """Download the specified files. Use the url to determine the domain.

    :param url: The URL containing the site's domain.
    :param files: List of directories containing the file paths.
    """
    tmp_dir = get_tmp_directory_path()
    scheme, netloc = urlparse(url).scheme, urlparse(url).netloc
    for that in files:
        # Construct the absolute url to the file
        file_url = urlparse(that['old'])
        file_url_path = file_url.path
        file_url = urlunsplit([scheme, netloc, file_url_path, '', ''])

        # The name of the subdir it will be stored in
        subdirectory = os.path.dirname(file_url_path)

        # Construct a path to where the file should be stored locally
        local_folder = os.path.join(tmp_dir, subdirectory)

        # Create the subdirectory structure if it doesn't exist
        if not os.path.exists(local_folder):
            os.makedirs(local_folder)

        # Construct the local file path to the file
        local_file_path = os.path.join(tmp_dir, file_url_path)

        # Save the file to the path if it doesn't already exist
        if not os.path.isfile(local_file_path):
            data = urlopen(file_url).read()
            with file(local_file_path, 'wb') as f:
                f.write(data)


def upload_files():
    """Upload all files from `get_tmp_directory_path()` to the FTP."""
    ftp = FTP(config.get('ftp', 'host'), config.get('ftp', 'username'),
              config.get('ftp', 'password'))
    full_path = 'wp-content/uploads/old_site'
    # Create the folder structure if it doesn't exist and set cwd to it
    for path in full_path.split('/'):
        try:
            ftp.mkd(path)
        except ftplib.error_perm as e:
            if e.message == '550 Can\'t create directory: File exists':
                pass
            else:
                raise e
        ftp.cwd(path)
        # Traverse all files in the tmp_dir and upload them
    tmp_dir = get_tmp_directory_path()
    prev_dir = tmp_dir
    for root, dirs, files in os.walk(tmp_dir):
        ftp.cwd(os.path.relpath(root, prev_dir))
        prev_dir = root
        # Create the dirs
        for that in dirs:
            try:
                ftp.mkd(that)
            except ftplib.error_perm as e:
                if e.message == '550 Can\'t create directory: File exists':
                    pass
                else:
                    raise e
                    # Upload the files if they don't already exist on the FTP
        for that in set(files).difference(ftp.nlst()[2:]):
            path = os.path.join(root, that)
            with open(path, 'rb') as f:
                ftp.storbinary('STOR {}'.format(that), f)
    ftp.quit()


def make_wordpress_page(title, content, publish, cookies):
    """Make a page on the WordPress blog.

    :param title: The page's title.
    :type title: str
    :param content: The page's content.
    :type content: str
    :param publish: If it should be marked as published.
    :param publish: bool
    :return: tuple -- of str title and str page link.
    :rtype: tuple
    """
    plugin = config.get('wordpress', 'plugin')

    if plugin == 'json-rest-api':
        url = os.path.join(config.get('wordpress', 'url'), 'wp-json.php/posts')
        auth = b64encode('{}:{}'.format(config.get('wordpress', 'username'),
                                        config.get('wordpress', 'password')))
        payload = {
            'title': title,
            'type': 'page',
            'content_raw': content,
            'status': 'publish' if publish else 'draft',
        }
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Basic {}'.format(auth),
        }
        r = requests.post(url, data=json.dumps(payload), headers=headers)
        response = json.loads(r.content)
        return response['title'], response['link']

    elif plugin == 'json-api':
        # Start with fetching the nonce
        url = os.path.join(config.get('wordpress', 'url'), 'api/get_nonce/')
        payload = {
            'controller': 'posts',
            'method': 'create_post',
        }
        headers = {
            'Cookie': cookies,
        }
        response = json.loads(
            requests.post(url, data=payload, headers=headers).content)
        nonce = response['nonce']

        # Next step is to make the post
        url = os.path.join(config.get('wordpress', 'url'),
                           'api/posts/create_post/')
        payload = {
            'title': title,
            'type': 'page',
            'content': content,
            'status': 'publish' if publish else 'draft',
            'nonce': nonce,
            'author': config.get('wordpress', 'username'),
            'user_password': config.get('wordpress', 'password'),
        }
        headers = {
            'Cookie': cookies,
        }
        r = requests.post(url, data=payload, headers=headers)
        response = json.loads(r.content)
        return response['post']['title'], response['post']['url']


def post(title, url, **kwargs):
    """Convert a HTML page and post it on WordPress.

    :param title: The title of the WordPress page.
    :type title: str
    :param url: The HTML page to be converted.
    :type url: str
    :param kwargs:
    :return: tuple -- of the formatted content, the returned title and the new
    url
    """
    content, files = parse(url, **kwargs)
    download_files(url, files)
    upload_files()
    publish = kwargs.get('publish', False)
    cookies = kwargs.get('cookies', '')
    wordpress_title, wordpress_page_url = make_wordpress_page(title, content,
                                                              publish, cookies)
    return content, wordpress_title, wordpress_page_url


if __name__ == '__main__':
    post(sys.argv[1], sys.argv[2], delete_links='')
