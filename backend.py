from ConfigParser import ConfigParser
from base64 import b64encode
from ftplib import FTP
import ftplib
import json
import os
from urllib import urlopen
from urlparse import urlparse, urlunsplit
from bs4 import BeautifulSoup, Tag
import requests


config = ConfigParser()
config.read(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                         'config.ini'))


def parse(url, **kwargs):
    """Parse the HTML page and return a tuple of the formatted content and the
    image links.

    :param url: The path to the HTML page.
    :type url: str.
    :param kwargs:
    :return: tuple -- the page content as a str and image image links as a list
    of str
    """
    soup = BeautifulSoup(urlopen(url))

    # Special thing for http://andersj.se
    if 'remove_new_window_link' in kwargs and kwargs['remove_new_window_link']:
        page = url.split('/')[-1]
        for a in soup.find_all('a'):
            if page == a['href']:
                p = a.parent.parent.parent.parent
                p.parent.contents.remove(p)

    # Update image src urls
    images = []
    for img in soup.find_all('img'):
        src = img['src']
        img['src'] = os.path.join(config.get('wordpress', 'url'),
                                  'wp-content/uploads/old_site/{}'.format(
                                      img['src']))
        images.append({'old': src, 'new': img['src']})

    # Get the content inside the body tag and the js scripts
    body_content = ''.join(
        [unicode(x) for x in soup.body.contents if type(x) == Tag])
    scripts = soup.head.find_all('script')

    # Put the body content and scripts together
    content = u'\n'.join([unicode(x) for x in scripts])
    content = unicode(content) + unicode(body_content)
    content = u'[raw]{}[/raw]'.format(content)
    content = BeautifulSoup(content).prettify()

    return content, images


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


def download_images(url, images):
    """Download the specified images. Use the url to determine the domain.

    :param url: The URL containing the site's domain.
    :param images: List of directories containing the image paths.
    """
    tmp_dir = get_tmp_directory_path()
    scheme, netloc = urlparse(url).scheme, urlparse(url).netloc
    for that in images:
        # Construct the url to the image
        img_url = urlparse(that['old'])
        img_url_path = img_url.path
        img_url = urlunsplit([scheme, netloc, img_url_path, '', ''])
        subdirectory = os.path.dirname(img_url_path)
        # Construct a local path inside the tmp dir using the subdirectory path
        local_folder = os.path.join(tmp_dir, subdirectory)
        # Create the subdirectory structure if it doesn't exist
        if not os.path.exists(local_folder):
            os.makedirs(local_folder)
            # Construct the local file path
        local_file_path = os.path.join(tmp_dir, img_url_path)
        # Save the image file to the path if it doesn't already exist
        if not os.path.isfile(local_file_path):
            data = urlopen(img_url).read()
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


def make_wordpress_page(title, content, published):
    """Make a page on the WordPress blog.

    :param title: The page's title.
    :type title: str
    :param content: The page's content.
    :type content: str
    :param published: If it should be marked as published.
    :param published: bool
    :return: tuple -- of str title and str page link.
    :rtype: tuple
    """
    url = os.path.join(config.get('wordpress', 'url'), 'wp-json.php/posts')
    auth = b64encode('{}:{}'.format(config.get('wordpress', 'username'),
                                    config.get('wordpress', 'password')))
    payload = {
        'title': title,
        'type': 'page',
        'content_raw': content,
        'status': 'published' if published else 'draft',
    }
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Basic {}'.format(auth),
    }
    r = requests.post(url, data=json.dumps(payload), headers=headers)
    response = json.loads(r.content)
    return response['title'], response['link']


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
    content, images = parse(url, **kwargs)
    download_images(url, images)
    upload_files()
    published = kwargs.get('published', False)
    wordpress_title, wordpress_page_url = make_wordpress_page(title, content,
                                                              published)
    return content, wordpress_title, wordpress_page_url
