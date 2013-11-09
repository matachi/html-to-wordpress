HTML To WordPress
=================

Convert simple HTML pages and make WordPress pages of them.

Author: Daniel 'MaTachi' Jonsson  
License: [MIT License](LICENSE)

Requirements
------------

Python 2.7 with the packages Flask, beautifulsoup4 and requests. They can, for example, be installed with:

```sh
$ pip install Flask beautifulsoup4 requests
```

It's recommended to use a virtualenv.

Either the WordPress plugin [JSON REST
API](http://wordpress.org/plugins/json-rest-api/) or the modified plugin
[JSON API](https://github.com/Achillefs/wp-json-api) (with support for making
posts) is also needed for this to work.

What the program does
---------------------

### 1. Flask front end

The font end is written with the web framework Flask, and it offers a field for
putting in the URL to the page to be converted and a field for the title of the
WordPress page that will be created. When submitting the form, it will make the
conversion and show a link to the newly created WordPress page.

### 2. Configuration

To make this work, you will need to specify some data inside
[config.ini](config.ini).  Necessary data is login details to the FTP, URL to
the WordPress root and login details to the WordPress blog.


### 3. Back end

The back end will start with getting the content inside the body tag and also
grab the script tags. Then it will grab and update all image source links. It
will put this together to later use this as the content of the WordPress page.

During the next step it downloads all referenced images and stores them inside
a folder called tmp.

The back end's next step is to upload all images on the FTP.

When that's done, it will continue with creating a WordPress page with the help
of a JSON REST API. Afterwards it will finally return with the URL to the newly
created page.
