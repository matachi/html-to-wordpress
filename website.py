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
                      publish=publish)
        template = render_template('posted.html', content=result[0],
                                   title=result[1], link=result[2])
        response = make_response(template)
        response.set_cookie('remove_new_window_link',
                            'true' if remove_new_window_link else 'false')
        response.set_cookie('publish', 'true' if publish else 'false')
        return response

    elif request.method == 'GET':
        publish = 'true' == request.cookies.get('publish')
        remove_new_window_link = 'true' == request.cookies.get(
            'remove_new_window_link')
        print(publish)
        return render_template('index.html', publish=publish,
                               remove_new_window_link=remove_new_window_link)


if __name__ == '__main__':
    app.run()
