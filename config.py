import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = 'change-this-secret-key'

    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://3UcDWkpsqj4NvF8.root:r749FoxYHfXibb4l@gateway01.ap-southeast-1.prod.aws.tidbcloud.com:4000/test"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SSL for TiDB Cloud
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {
            "ssl": {"ca": "E:/college events handle projects/isrgrootx1.pem"}
        }
    }
