def test_basic():
    assert True

def test_import():
    from flask import Flask
    app = Flask(__name__)
    assert app is not None