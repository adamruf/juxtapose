from flask import Flask, request, session, redirect, url_for, \
    render_template, jsonify, abort, send_from_directory
import os
import sys
import importlib
import uuid
import json
import traceback
import boto


# Import settings module
if __name__ == "__main__":
    if not os.environ.get('FLASK_SETTINGS_MODULE', ''):
        os.environ['FLASK_SETTINGS_MODULE'] = 'core.settings.loc'

settings_module = os.environ.get('FLASK_SETTINGS_MODULE')

try:
    importlib.import_module(settings_module)
except ImportError, e:
    raise ImportError("Could not import settings '%s' (Is it on sys.path?): %s" % (settings_module, e))


app = Flask(__name__)
app.config.from_envvar('FLASK_CONFIG_MODULE')

settings = sys.modules[settings_module]

build_dir = os.path.join(settings.JUXTAPOSE_ROOT, 'build')
source_dir = os.path.join(settings.JUXTAPOSE_ROOT, 'juxtapose')

@app.context_processor
def inject_urls():
    """
    Inject urls into the templates.
    Template variable will always have a trailing slash.
    """
    static_url = settings.STATIC_URL or app.static_url_path
    if not static_url.endswith('/'):
        static_url += '/'

    storage_url = settings.AWS_STORAGE_BUCKET_URL
    if not storage_url.endswith('/'):
        storage_url += '/'
    storage_url += settings.AWS_STORAGE_BUCKET_KEY
    if not storage_url.endswith('/'):
        storage_url += '/'

    cdn_url = settings.CDN_URL
    if not cdn_url.endswith('/'):
        cdn_url += '/'

    return dict(
        STATIC_URL=static_url, static_url=static_url,
        STORAGE_URL=storage_url, storage_url=storage_url,
        CDN_URL=cdn_url, cdn_url=cdn_url)



@app.route('/')
@app.route('/<path:path>')
def catch_all(path='index.html', context=None):
    """Catch-all function which serves every URL."""
    context = context or {}
    if not os.path.splitext(path)[1]:
        path = os.path.join(path, 'index.html')
    return render_template(path, **context)


@app.route('/juxtapose/<path:path>')
@app.route('/source/<path:path>')
@app.route('/images/<path:path>')
def catch_source(path):
    """
    Serve /source/... urls from the source directory
    """
    return send_from_directory(source_dir, path)



# Juxtapose API
def _get_uid():
    """Generate a unique identifer for slider"""
    return uuid.uuid1().urn.split(':')[2]


@app.route('/juxtapose/create/', methods=['POST'])
def upload_juxtapose_json():
    """Post JSON to S3 Bucket"""
    try:
        data = request.json
        uid = _get_uid()
        s3 = boto.connect_s3(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
        bucket = s3.get_bucket(settings.AWS_STORAGE_BUCKET_NAME)
        k = boto.s3.key.Key(bucket)
        k.key = 'juxtapose/' + uid + '.json'
        k.set_contents_from_string(json.dumps(data), policy='public-read')
        if request.host == 'juxtapose.knilab.com':
            uid = 'https://s3.amazonaws.com/uploads.knilab.com/%s' % k.key
        return jsonify({'uid': uid})
    except Exception, e:
        traceback.print_exc()
        return jsonify({'error': str(e)})

    
        
if __name__ == "__main__":
    import getopt
    
    ssl_context = None
    port = 5000
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "sp:", ["port="])
        for opt, arg in opts:
            if opt == '-s':
                ssl_context = (
                    os.path.join(site_dir, 'website.crt'), 
                    os.path.join(site_dir, 'website.key'))

            elif opt in ('-p', '--port'):
                port = int(arg)
            else:
                print 'Usage: app.py [-s]'
                sys.exit(1)   
    except getopt.GetoptError:
        print 'Usage: app.py [-s] [-p port]'
        sys.exit(1)
       
    app.run(host='0.0.0.0', port=5000, debug=True, ssl_context=ssl_context)
