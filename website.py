import sys
from flask import Flask, render_template, request, make_response
from backend import post


app = Flask(__name__)


@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        remove_new_window_link = True if request.form.get(
            'remove_new_window_link', False) else False
        publish = True if request.form.get('publish', False) else False
        result = post(request.form['title'],
                      request.form['url'],
                      remove_new_window_link=remove_new_window_link,
                      publish=publish,
                      delete_links=request.form['delete_links'])
        template = render_template('posted.html', content=result[0],
                                   title=result[1], link=result[2])
        response = make_response(template)
        response.set_cookie('remove_new_window_link',
                            'true' if remove_new_window_link else 'false')
        response.set_cookie('publish', 'true' if publish else 'false')
        response.set_cookie('delete_links', request.form['delete_links'])
        return response

    elif request.method == 'GET':
        publish = 'true' == request.cookies.get('publish')
        remove_new_window_link = 'true' == request.cookies.get(
            'remove_new_window_link')
        delete_links = request.cookies.get('delete_links', '')
        return render_template('index.html', publish=publish,
                               remove_new_window_link=remove_new_window_link,
                               delete_links=delete_links)


if __name__ == '__main__':
    host = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
    app.run(debug=True, host=host)
