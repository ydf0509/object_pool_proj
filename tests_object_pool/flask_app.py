import flask

app = flask.Flask(__name__)

@app.route('/')
def index():
    return 'hello flask'


if __name__ == '__main__':
    app.run(port=8887)