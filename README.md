# fragforce.org
## Deployment Instructions
1. Install the following system packages if they are not already installed:
  * python2.7
  * nginx
  * virtualenv
2. run ```virtualenv env``` to create the virtual environment for the server
3. activate the virtual environment with ```. env/bin/activate```
4. run ```pip install -r requirements.txt``` to install the remaining dependencies into the virtual environment.
  * This will fail on FreeBSD because the gmp.h file for pycrypto is not in the default path, run the following 2 commands to resolve and re-run step 4 above:

    ```
    export CPPFLAGS="-I/usr/local/include $CPPFLAGS"
    export LDFLAGS="-L/usr/local/lib $LDFLAGS"
    ```
  * Serving SVG files on FreeBSD will also fail due to missing mime-support port in ```misc/mime-support```
5. To verify that it works, simply run ```python run.py``` to start a local server running on port 8000 for verification/development
6. Create a new nginx server config for your server with the following data: 

    ```
    server {
        listen       80;
        server_name  dev.fragforce.org localhost;

        access_log  /var/log/nginx/fragforce-test.org.access.log;
        error_log /var/log/nginx/fragforce-test.org.error.log;

        location / {
            try_files $uri @fragforce;
        }
        location @fragforce {
            include uwsgi_params;
            uwsgi_pass unix:/tmp/fragforce.sock;
        }
    }
    ```
  * Modify the listen port and server_name to your environment
7. Restart nginx
8. Run uwsgi in the project directory via ```uwsgi -s /tmp/fragforce.sock --module fragforce --callable app -H <PATH TO VIRTUALENV ENV DIRECTORY>```
9. ```chmod 777 /tmp/fragforce.sock```



Jenkins Build Test
BLARGH
