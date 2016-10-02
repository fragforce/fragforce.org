# Run a local debug server
import argparse
from fragforce import app


def run(app, default_host="0.0.0.0", default_port=8000):
    parser = argparse.ArgumentParser()

    parser.add_argument("-H", "--host",
                        help=("Hostname for the Flask app [default {}]"
                              .format(default_host)))

    parser.add_argument("-P", "--port", default=default_port, type=int,
                        help=("Port for the Flask app [default {}]"
                              .format(default_port)))

    parser.add_argument("-d", "--debug", action="store_true",
                        help="Run the server in debug mode")

    args = parser.parse_args()

    app.run(debug=args.debug, host=args.host, port=args.port)


if __name__ == "__main__":
    run(app)
